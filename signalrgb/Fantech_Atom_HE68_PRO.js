/*
 * Unofficial SignalRGB HID plugin for the Fantech Atom HE68 PRO.
 *
 * Custom lighting is a 128-entry RGB table sent in ten 64-byte reports.
 * This implementation is derived only from captures made with the official
 * configurator. Q/W/E/R/T/Y addresses are capture-confirmed; the remaining
 * physical address map follows the same 16-column keyboard matrix and should
 * be tested on the device before this plugin is submitted upstream.
 */

const VENDOR_ID = 0x0C45;
const PRODUCT_ID = 0x80CB;
const VENDOR_USAGE_PAGE = 0xFF68;
const TABLE_SIZE = 128;
const REPORT_LENGTH = 65; // SignalRGB HID writes include the leading report ID 0.
const BATTERY_UPDATE_INTERVAL = 360; // ~65 seconds at the wired plugin's ~5.5 FPS limit
const BATTERY_STATE_CHARGING = 2;
const BATTERY_STATE_FULL = 4;
const BATTERY_QUERY_PAYLOAD = [
    0xAA, 0x10, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
];

// [firmware RGB-table address, SignalRGB key name, x, y]
// Known capture mapping: Tab=32, Q=33, W=34, E=35, R=36, T=37, Y=38.
const LED_MAP = [
    [0, "Esc", 0, 0], [17, "1", 1, 0], [18, "2", 2, 0], [19, "3", 3, 0],
    [20, "4", 4, 0], [21, "5", 5, 0], [22, "6", 6, 0], [23, "7", 7, 0],
    [24, "8", 8, 0], [25, "9", 9, 0], [26, "0", 10, 0], [27, "-", 11, 0],
    [28, "=", 12, 0], [92, "Backspace", 13, 0], [103, "Insert", 14, 0],

    [32, "Tab", 0, 1], [33, "Q", 1, 1], [34, "W", 2, 1], [35, "E", 3, 1],
    [36, "R", 4, 1], [37, "T", 5, 1], [38, "Y", 6, 1], [39, "U", 7, 1],
    [40, "I", 8, 1], [41, "O", 9, 1], [42, "P", 10, 1], [43, "[", 11, 1],
    [44, "]", 12, 1], [60, "\\", 13, 1], [106, "Del", 14, 1],

    [48, "Caps Lock", 0, 2], [49, "A", 1, 2], [50, "S", 2, 2], [51, "D", 3, 2],
    [52, "F", 4, 2], [53, "G", 5, 2], [54, "H", 6, 2], [55, "J", 7, 2],
    [56, "K", 8, 2], [57, "L", 9, 2], [58, ";", 10, 2], [59, "'", 11, 2],
    [76, "Enter", 13, 2], [105, "Page Up", 14, 2],

    [64, "Left Shift", 0, 3], [65, "Z", 2, 3], [66, "X", 3, 3], [67, "C", 4, 3],
    [68, "V", 5, 3], [69, "B", 6, 3], [70, "N", 7, 3], [71, "M", 8, 3],
    [72, ",", 9, 3], [73, ".", 10, 3], [74, "/", 11, 3], [75, "Right Shift", 12, 3],
    [90, "Up Arrow", 13, 3], [108, "Page Down", 14, 3],

    [80, "Left Ctrl", 0, 4], [81, "Left Win", 1, 4], [82, "Left Alt", 2, 4],
    [83, "Space", 7, 4], [84, "Right Alt", 9, 4], [85, "Fn", 10, 4],
    [87, "Right Ctrl", 11, 4], [88, "Left Arrow", 12, 4], [89, "Down Arrow", 13, 4],
    [91, "Right Arrow", 14, 4]
];

const CUSTOM_MODE_PACKET = [
    0xAA, 0x23, 0x10, 0x00, 0x00, 0x00, 0x01, 0x00,
    0x80, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00,
    0x01, 0x05, 0x04, 0x00, 0x00, 0x00, 0xAA, 0x55
].concat(new Array(40).fill(0));
let renderCount = 0;

export function Name() { return "Fantech Atom HE68 PRO (Unofficial)"; }
export function Publisher() { return "HE68 community reverse-engineering project"; }
export function ImageUrl() { return "https://cdn.shopify.com/s/files/1/0630/1689/4649/files/Product_Icon_Atom_HE68_PRO_MK922.png?v=1761649745"; }
export function VendorId() { return VENDOR_ID; }
export function ProductId() { return PRODUCT_ID; }
export function Type() { return "hid"; }
export function Size() { return [15, 5]; }
export function DefaultPosition() { return [0, 0]; }
export function DefaultScale() { return 8.0; }
export function LedNames() { return LED_MAP.map((led) => led[1]); }
export function LedPositions() { return LED_MAP.map((led) => [led[2], led[3]]); }

export function Validate(endpoint) {
    return endpoint.usage_page === VENDOR_USAGE_PAGE;
}

export function Initialize() {
    device.addFeature("battery");
    battery.setBatteryState(BATTERY_STATE_CHARGING);
    updateBattery();
    // Observed official-software action: select Custom lighting mode.
    writePayload(CUSTOM_MODE_PACKET);
    drainResponse();
}

export function Render() {
    renderCount += 1;
    if (renderCount % BATTERY_UPDATE_INTERVAL === 0) updateBattery();
    const table = Array.from({ length: TABLE_SIZE }, () => [0, 0, 0]);
    for (const [address, , x, y] of LED_MAP) {
        table[address] = device.color(x, y);
    }
    sendCustomTable(table);
    // Ten HID writes form one keyboard frame; keep the device near 5 FPS.
    device.pause(180);
}

export function Shutdown() {
    // No safe "restore previous hardware effect" command has been captured.
    // Leaving the final Custom frame visible is safer than guessing one.
}

function sendCustomTable(table) {
    for (let start = 0; start < TABLE_SIZE; start += 14) {
        const count = Math.min(14, TABLE_SIZE - start);
        const payload = new Array(64).fill(0);
        payload[0] = 0xAA;
        payload[1] = 0x24;
        payload[2] = count * 4;
        const offset = start * 4;
        payload[3] = offset & 0xFF;
        payload[4] = (offset >> 8) & 0xFF;
        payload[5] = (offset >> 16) & 0xFF;
        payload[6] = start + count === TABLE_SIZE ? 1 : 0;
        let cursor = 8;
        for (let address = start; address < start + count; address += 1) {
            const color = table[address];
            payload[cursor] = address;
            payload[cursor + 1] = color[0];
            payload[cursor + 2] = color[1];
            payload[cursor + 3] = color[2];
            cursor += 4;
        }
        writePayload(payload);
        drainResponse();
    }
}

function writePayload(payload) {
    // SignalRGB's HID API requires the report-ID zero before our captured
    // 64-byte WebHID payload, and pads to the explicitly requested length.
    device.write([0].concat(payload), REPORT_LENGTH);
}

function drainResponse() {
    // Custom-table writes have observed responses, but their semantics are not
    // decoded. Drain them non-blockingly so the endpoint cannot fill up.
    device.read([], REPORT_LENGTH, 0);
}

function drainPendingResponses() {
    for (let attempt = 0; attempt < 32; attempt += 1) {
        device.read([], REPORT_LENGTH, 0);
        if (device.getLastReadSize() <= 0) return;
    }
}

function readBatteryResponse() {
    for (let attempt = 0; attempt < 20; attempt += 1) {
        const response = device.read([], REPORT_LENGTH, 0);
        if (device.getLastReadSize() > 0) {
            const reportOffset = response[0] === 0x00 ? 1 : 0;
            if (response[reportOffset] === 0x55 &&
                response[reportOffset + 1] === 0x10 &&
                response[reportOffset + 2] === 0x18) return [response, reportOffset];
        }
        device.pause(5);
    }
    return null;
}

function updateBattery() {
    // The wireless capture's 55 10 18 reply identifies keyboard PID 0x80CB,
    // so use the same firmware query on the wired 64-byte HID endpoint.
    drainPendingResponses();
    writePayload(BATTERY_QUERY_PAYLOAD);
    device.pause(15);
    const result = readBatteryResponse();
    if (result === null) return;
    const [response, reportOffset] = result;

    const encodedLevel = response[reportOffset + 11];
    const level = ((encodedLevel >> 4) * 10) + (encodedLevel & 0x0F);
    if (level >= 0 && level <= 100) {
        battery.setBatteryLevel(level);
        // A valid reply on this endpoint means USB power is present. The packet
        // has no proven charge flag, so derive the state from the wired transport.
        battery.setBatteryState(level === 100 ? BATTERY_STATE_FULL : BATTERY_STATE_CHARGING);
    }
}
