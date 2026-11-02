// StartSense Main Client Logic

// 1. Update Mock Potentiometer
function updatePotentiometer(val) {
    document.getElementById("sidebar-adc-val").innerText = val;
    let volts = ((val / 4095.0) * 3.3).toFixed(2);
    let norm = ((val / 4095.0) * 100).toFixed(1);
    document.getElementById("sidebar-volts-val").innerText = volts;
    document.getElementById("sidebar-load-val").innerText = norm + "%";

    fetch("/api/mock_pot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ adc: parseInt(val) })
    });
}

// 2. Connect Serial Link
function connectSerial() {
    const port = document.getElementById("sidebar-com-port").value;
    fetch("/api/serial/connect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port: port, baudrate: 115200 })
    })
    .then(res => res.json())
    .then(data => {
        updateLinkBadge(data);
        if (data.status !== "OK" && port !== "MOCK") {
            alert(data.message || "Failed to open " + port);
        }
    });
}

// 3. Disconnect Serial Link
function disconnectSerial() {
    fetch("/api/serial/disconnect", { method: "POST" })
    .then(res => res.json())
    .then(data => {
        updateLinkBadge({ is_connected: false, is_mock_mode: true });
    });
}

// 4. Update Badge UI
function updateLinkBadge(state) {
    const badge = document.getElementById("sidebar-link-badge");
    if (!badge) return;
    if (state.is_connected && !state.is_mock_mode) {
        badge.className = "badge-hardware mb-3 text-center py-1";
        badge.innerText = "● HARDWARE CONNECTED (" + (state.port || "USB") + ")";
    } else {
        badge.className = "badge-mock mb-3 text-center py-1";
        badge.innerText = "● MOCK MODE ACTIVE";
    }
}

// 5. Periodic Polling for Live Potentiometer & Link Status (every 1.5s)
setInterval(() => {
    fetch("/api/status")
    .then(res => res.json())
    .then(data => {
        if (data.pot) {
            document.getElementById("sidebar-adc-val").innerText = data.pot.adc_raw;
            document.getElementById("sidebar-volts-val").innerText = data.pot.voltage.toFixed(2);
            document.getElementById("sidebar-load-val").innerText = (data.pot.normalized * 100).toFixed(1) + "%";
            const slider = document.getElementById("pot-slider");
            if (slider && document.activeElement !== slider) {
                slider.value = data.pot.adc_raw;
            }
        }
        updateLinkBadge(data.link);
    })
    .catch(() => {});
}, 1500);
