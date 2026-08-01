/* Paste in DevTools before using the official WebHID software. Removes itself on reload. */
(() => {
  if (!globalThis.HIDDevice) throw new Error("WebHID is unavailable on this page.");
  if (window.__he68Recorder) return window.__he68Recorder.show();
  const REPORT_LENGTH = 64, hex = data => [...new Uint8Array(data)].map(x => x.toString(16).padStart(2, "0")).join(" ").toUpperCase();
  const state = { recording: false, packets: [], captureName: "capture", stoppedAutomatically: false, device: null };
  const originalSend = HIDDevice.prototype.sendReport;
  const originalDispatch = HIDDevice.prototype.dispatchEvent;
  function describeDevice(device) {
    return {
      vendor_id: device.vendorId,
      product_id: device.productId,
      product_name: device.productName,
      collections: (device.collections || []).map(collection => ({
        usage_page: collection.usagePage,
        usage: collection.usage,
        input_reports: (collection.inputReports || []).map(report => ({ report_id: report.reportId, bytes: report.items?.reduce((total, item) => total + (item.reportSize || 0) * (item.reportCount || 0) / 8, 0) ?? null })),
        output_reports: (collection.outputReports || []).map(report => ({ report_id: report.reportId, bytes: report.items?.reduce((total, item) => total + (item.reportSize || 0) * (item.reportCount || 0) / 8, 0) ?? null }))
      }))
    };
  }
  function add(direction, data, reportId = null, device = null) {
    const bytes = ArrayBuffer.isView(data) ? new Uint8Array(data.buffer, data.byteOffset, data.byteLength) : new Uint8Array(data);
    if (!state.device && device) state.device = describeDevice(device);
    state.packets.push({ direction, report_id: reportId, payload_hex: hex(bytes).replaceAll(" ", ""), timestamp: new Date().toISOString() });
    render(); validateAndStop();
  }
  HIDDevice.prototype.sendReport = async function (reportId, data) {
    if (state.recording) add("host_to_device", data, reportId, this);
    return originalSend.call(this, reportId, data);
  };
  HIDDevice.prototype.dispatchEvent = function (event) {
    if (state.recording && event.type === "inputreport") add("device_to_host", event.data, event.reportId, this);
    return originalDispatch.call(this, event);
  };
  const panel = document.createElement("section");
  panel.style.cssText = "position:fixed;top:16px;right:16px;z-index:2147483647;width:310px;padding:14px;border-radius:12px;background:#151821;color:#fff;font:13px system-ui;box-shadow:0 8px 32px #0008";
  panel.innerHTML = `<b style="font-size:16px">HE68 Capture Recorder</b><label style="display:block;margin-top:12px">Capture Name <input id="hname" value="capture" style="width:100%;box-sizing:border-box;margin-top:4px"></label><p><button id="hstart">Start Recording</button> <button id="hstop">Stop Recording</button> <button id="hsave">Save Capture</button></p><div id="hcount"></div><pre id="hlive" style="max-height:180px;overflow:auto;white-space:pre-wrap;background:#0c0e13;padding:8px"></pre>`;
  document.body.append(panel);
  const $ = id => panel.querySelector(id), download = () => {
    state.captureName = $("#hname").value.trim() || "capture";
    const blob = new Blob([JSON.stringify({ format: "he68.webhid.capture.v2", capture_name: state.captureName, device: state.device, packets: state.packets }, null, 2)], {type:"application/json"});
    const a = Object.assign(document.createElement("a"), {href: URL.createObjectURL(blob), download: `${state.captureName}.json`}); a.click(); URL.revokeObjectURL(a.href);
  };
  function validateAndStop() {
    const tx = state.packets.filter(x => x.direction === "host_to_device"), rx = state.packets.filter(x => x.direction === "device_to_host");
    if (tx.length === 1 && rx.length === 1 && rx[0].payload_hex.startsWith("552310")) { state.recording = false; state.stoppedAutomatically = true; download(); }
  }
  function render() {
    const tx = state.packets.filter(x => x.direction === "host_to_device"), rx = state.packets.filter(x => x.direction === "device_to_host");
    const warnings = []; if (!rx.some(x => x.payload_hex.startsWith("552310"))) warnings.push("No ACK"); if (tx.length > 1) warnings.push("Multiple requests"); if (state.packets.some(x => x.payload_hex.length !== REPORT_LENGTH * 2)) warnings.push("Unknown packet length");
    $("#hcount").textContent = `Packets: ${state.packets.length} | Host -> Device: ${tx.length} | Device -> Host: ${rx.length}${warnings.length ? " | WARNING: " + warnings.join(", ") : ""}`;
    $("#hlive").textContent = state.packets.slice(-8).map(x => `${x.direction === "host_to_device" ? "TX" : "RX"} #${x.report_id ?? "?"}  ${x.payload_hex.match(/../g).join(" ")}`).join("\n");
  }
  $("#hstart").onclick = () => { state.packets = []; state.device = null; state.recording = true; state.stoppedAutomatically = false; render(); };
  $("#hstop").onclick = () => { state.recording = false; render(); };
  $("#hsave").onclick = download;
  window.__he68Recorder = { show: () => panel.hidden = false, start: $("#hstart").onclick, stop: $("#hstop").onclick, save: download };
  render();
})();
