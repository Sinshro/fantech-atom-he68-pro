/* Unofficial SignalRGB 2.4 GHz dongle plugin for the Fantech Atom HE68 PRO.
 * Capture verified: Custom lighting uses 22 32-byte reports, six RGB entries
 * per report, then a two-entry committing report. */

const TABLE_SIZE = 128;
const REPORT_LENGTH = 33; // leading report-ID zero + 32-byte payload
const CUSTOM_MODE_PAYLOAD = [
    0xAA,0x23,0x10,0x00,0x00,0x00,0x01,0x00,
    0x80,0xFF,0xFF,0xFF,0xFF,0x00,0x00,0x00,
    0x01,0x05,0x04,0x00,0x00,0x00,0xAA,0x55,
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00
];
const LED_MAP = [
    [0,"Esc",0,0],[17,"1",1,0],[18,"2",2,0],[19,"3",3,0],[20,"4",4,0],[21,"5",5,0],[22,"6",6,0],[23,"7",7,0],[24,"8",8,0],[25,"9",9,0],[26,"0",10,0],[27,"-",11,0],[28,"=",12,0],[92,"Backspace",13,0],[103,"Insert",14,0],
    [32,"Tab",0,1],[33,"Q",1,1],[34,"W",2,1],[35,"E",3,1],[36,"R",4,1],[37,"T",5,1],[38,"Y",6,1],[39,"U",7,1],[40,"I",8,1],[41,"O",9,1],[42,"P",10,1],[43,"[",11,1],[44,"]",12,1],[60,"\\",13,1],[106,"Del",14,1],
    [48,"Caps Lock",0,2],[49,"A",1,2],[50,"S",2,2],[51,"D",3,2],[52,"F",4,2],[53,"G",5,2],[54,"H",6,2],[55,"J",7,2],[56,"K",8,2],[57,"L",9,2],[58,";",10,2],[59,"'",11,2],[76,"Enter",13,2],[105,"Page Up",14,2],
    [64,"Left Shift",0,3],[65,"Z",2,3],[66,"X",3,3],[67,"C",4,3],[68,"V",5,3],[69,"B",6,3],[70,"N",7,3],[71,"M",8,3],[72,",",9,3],[73,".",10,3],[74,"/",11,3],[75,"Right Shift",12,3],[90,"Up Arrow",13,3],[108,"Page Down",14,3],
    [80,"Left Ctrl",0,4],[81,"Left Win",1,4],[82,"Left Alt",2,4],[83,"Space",7,4],[84,"Right Alt",9,4],[85,"Fn",10,4],[87,"Right Ctrl",11,4],[88,"Left Arrow",12,4],[89,"Down Arrow",13,4],[91,"Right Arrow",14,4]
];

export function Name() { return "Fantech Atom HE68 PRO Dongle (Unofficial)"; }
export function Publisher() { return "HE68 community reverse-engineering project"; }
export function ImageUrl() { return "https://cdn.shopify.com/s/files/1/0630/1689/4649/files/Product_Icon_Atom_HE68_PRO_MK922.png?v=1761649745"; }
export function VendorId() { return 0x0C45; }
export function ProductId() { return 0xFEFE; }
export function Type() { return "hid"; }
export function Size() { return [15, 5]; }
export function DefaultPosition() { return [0, 0]; }
export function DefaultScale() { return 8.0; }
export function LedNames() { return LED_MAP.map((led) => led[1]); }
export function LedPositions() { return LED_MAP.map((led) => [led[2], led[3]]); }

export function Validate(endpoint) {
    // The receiver's RGB collection is Windows interface MI_03. SignalRGB
    // 2.5.74 no longer consistently exposes usage_page/usage during its first
    // HID validation pass, so validating only those fields can prevent the
    // device engine from starting even though the correct dongle was found.
    return endpoint.interface === 3;
}

export function Initialize() {
    // Effect 0x80 is the captured Custom-lighting mode selector. The RGB table
    // can be updated while another onboard effect remains visible, so activate
    // Custom explicitly whenever SignalRGB opens the receiver.
    writePayload(CUSTOM_MODE_PAYLOAD);
    device.pause(50);
}

export function Render() {
    const table = Array.from({ length: TABLE_SIZE }, () => [0, 0, 0]);
    for (const [address, , x, y] of LED_MAP) table[address] = device.color(x, y);
    for (let start = 0; start < TABLE_SIZE; start += 6) {
        const count = Math.min(6, TABLE_SIZE - start);
        const payload = new Array(32).fill(0);
        payload[0] = 0xAA; payload[1] = 0x24; payload[2] = count * 4;
        const offset = start * 4;
        payload[3] = offset & 0xFF; payload[4] = (offset >> 8) & 0xFF;
        payload[5] = (offset >> 16) & 0xFF; payload[6] = start + count === TABLE_SIZE ? 1 : 0;
        let cursor = 8;
        for (let address = start; address < start + count; address += 1) {
            const color = table[address];
            payload[cursor] = address; payload[cursor + 1] = color[0];
            payload[cursor + 2] = color[1]; payload[cursor + 3] = color[2]; cursor += 4;
        }
        writePayload(payload); drainResponse();
        // The official wireless configurator spaces consecutive 32-byte table
        // reports by ~26 ms. Without it, the receiver drops later table chunks.
        device.pause(26);
    }
    // 22 × 26 ms means the receiver's capture-backed maximum is ~1.7 FPS.
}

export function Shutdown() { /* Preserve the last rendered Custom frame. */ }

function writePayload(payload) { device.write([0].concat(payload), REPORT_LENGTH); }
function drainResponse() { device.read([], REPORT_LENGTH, 0); }
