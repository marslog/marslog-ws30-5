// monitoring.js – Enhanced for Enterprise Monitoring

const $ = sel => document.querySelector(sel);
const $$ = sel => [...document.querySelectorAll(sel)];
const API = "/api";
let devices = [], pollingTimer = null;

// ========== INIT ==========
document.addEventListener("DOMContentLoaded", () => {
  attachUIHandlers();
  loadDevices();
});

function attachUIHandlers() {
  const btn = $("#btnTestConn");
  if (btn) btn.addEventListener("click", testConnection);

  const form = $("#addDeviceForm");
  if (form) {
    form.addEventListener("submit", async e => {
      e.preventDefault();
      await saveDevice(new FormData(e.target));
    });
  }

  const dropdown = $("#intervalDropdown");
  if (dropdown) dropdown.addEventListener("change", restartPolling);
}

// ========== CRUD ==========
async function loadDevices() {
  try {
    console.log("=== Loading devices from API ===");
    const res = await fetch(`${API}/devices`);
    console.log("API Response status:", res.status, res.statusText);
    console.log("API Response headers:", [...res.headers.entries()]);
    
    if (!res.ok) {
      console.error("API Error:", res.status, res.statusText);
      const errorText = await res.text();
      console.error("Error response:", errorText);
      return;
    }
    
    const responseText = await res.text();
    console.log("Raw API Response:", responseText);
    
    try {
      devices = JSON.parse(responseText);
      console.log("Devices parsed successfully:", devices.length, devices);
    } catch (parseError) {
      console.error("JSON Parse error:", parseError);
      console.error("Response was:", responseText);
      return;
    }
    
    console.log("=== About to render table ===");
    renderTable();
    console.log("=== About to restart polling ===");
    restartPolling();
  } catch (err) {
    console.error("Load error", err);
    console.error("Error stack:", err.stack);
  }
}

async function saveDevice(fd) {
  // ซ่อนข้อความ test connection ทันทีเมื่อกด Add Device
  const resultEl = document.querySelector("#testConnResult");
  if (resultEl) {
    resultEl.textContent = "";                  // วิธีที่ 1: เคลียร์ข้อความ
    // resultEl.style.display = "none";        // วิธีที่ 2: ซ่อนไปเลยก็ได้
  }

  const payload = Object.fromEntries(fd.entries());
  const id = payload.id;
  delete payload.id;

  const method = id ? "PUT" : "POST";
  const url = id ? `${API}/devices/${id}` : `${API}/devices`;

  try {
    const res = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(await res.text());
    closeModal();
    await loadDevices();
  } catch (err) {
    console.error("Save error", err);
  }
}

async function deleteDevice(id) {
  try {
    const res = await fetch(`${API}/devices/${id}`, { method: "DELETE" });
    await loadDevices();
  } catch (err) {
    console.error("Delete error", err);
  }
}

// ========== POLLING ==========
function restartPolling() {
  if (pollingTimer) clearInterval(pollingTimer);
  const interval = +($("#intervalDropdown")?.value || 300); // Changed default from 120 to 300 seconds (5 minutes)
  console.log(`Setting polling interval to ${interval} seconds`);
  pollAll();
  pollingTimer = setInterval(pollAll, interval * 1000);
}

function pollAll() {
  devices.forEach(pollOne);
}

async function pollOne(dev) {
  const row = document.querySelector(`tr[data-id='${dev.id}']`);
  if (!row) return;
  const st = row.querySelector(".status-cell");
  const lt = row.querySelector(".latency-cell");

  try {
    const t0 = performance.now();
    const url = `${API}/device_status?ip=${dev.ip}&method=${dev.method}`;
    const res = await fetch(url);
    const result = await res.json();
    const ok = result.status === "online";
    st.textContent = ok ? "Online" : "Offline";
    st.className = `status-cell font-bold ${ok ? "text-green-400" : "text-red-400"}`;
    lt.textContent = result.latency_ms ? `${result.latency_ms} ms` : "-";
  } catch {
    st.textContent = "Error";
    st.className = "status-cell text-yellow-400 font-bold";
    lt.textContent = "-";
  }
}

// ========== RENDER ==========
function renderTable() {
  console.log("=== renderTable() called ===");
  console.log("Devices array:", devices);
  console.log("Devices length:", devices.length);
  
  const tbody = $("#deviceTableBody");
  console.log("Table body element found:", !!tbody);
  console.log("Table body element:", tbody);
  
  if (!tbody) {
    console.error("❌ Table body element not found! Looking for #deviceTableBody");
    // ลองหา elements อื่นๆ
    console.log("All elements with 'table' in id:", document.querySelectorAll("[id*='table']"));
    console.log("All tbody elements:", document.querySelectorAll("tbody"));
    return;
  }
  
  if (!devices || devices.length === 0) {
    console.log("⚠️ No devices to render");
    tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-400">No devices found</td></tr>';
    return;
  }
  
  console.log("📝 Generating HTML for", devices.length, "devices");
  
  const html = devices.map((d, index) => {
    console.log(`Device ${index}:`, d);
    return `
    <tr data-id="${d.id}">
      <td class="px-6 py-4">${d.name || "-"}</td>
      <td class="px-6 py-4">${d.ip}</td>
      <td class="px-6 py-4">${d.method}</td>
      <td class="px-6 py-4">${d.template ? d.template : '<span class="text-gray-500 italic">None</span>'}</td>
      <td class="status-cell font-bold text-gray-400 px-6 py-4">wait</td>
      <td class="latency-cell px-6 py-4">-</td>
      <td class="px-6 py-4">
        <button class="edit-btn bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded mr-2" onclick="openAddModal('${d.id}')">✎</button>
        <button class="delete-btn bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded" onclick="deleteDevice('${d.id}')">🗑</button>
      </td>
    </tr>
  `;
  }).join("");
  
  console.log("Generated HTML length:", html.length);
  console.log("Generated HTML preview:", html.substring(0, 200) + "...");
  console.log("Setting tbody.innerHTML...");
  tbody.innerHTML = html;
  console.log("✅ Table rendered successfully");
}

// ========== MODAL ==========
function openAddModal(id = null) {
  const modal = $("#addDeviceModal");
  modal.classList.remove("hidden");
  const form = $("#addDeviceForm");
  const title = $("#modalTitle") || modal.querySelector("h3");

  if (id) {
    const dev = devices.find(x => x.id === id);
    if (dev) {
      title.textContent = "Edit Device";
      form.reset();
      for (const [key, val] of Object.entries(dev)) {
        const field = form.querySelector(`[name='${key}']`);
        if (field) field.value = val;
      }
      form.querySelector("input[name='id']")?.remove();
      form.insertAdjacentHTML("beforeend", `<input type='hidden' name='id' value='${id}'>`);
    }
  } else {
    title.textContent = "Add New Device";
    form.reset();
    form.querySelector("input[name='id']")?.remove();
  }
  const resultEl = document.querySelector("#testConnResult");
if (resultEl) resultEl.textContent = "⏳ Testing…";

}

const closeModal = () => $("#addDeviceModal").classList.add("hidden");

// ========== TEST CONNECTION ==========
async function testConnection() {
  const ip     = $("input[name='ip']")?.value;
  const method = $("select[name='method']")?.value;
  const result = $("#testConnResult");

  if (!ip || !method) {
 Swal.fire({
  icon: 'warning',
  title: 'Are you sure?',
  text: 'Please enter both IP Address and Monitoring Method',
  background: '#1e1b2e', // สีพื้นหลังแนวม่วงเข้ม (เหมือน logout)
  color: '#e5e7eb',      // ตัวอักษรสีอ่อน
  iconColor: '#facc15',  // สีไอคอน (เหลือง)
  showCancelButton: false,
  confirmButtonText: 'OK',
  confirmButtonColor: '#6366f1', // ปุ่มม่วงแบบ Tailwind 'indigo-500'
  customClass: {
    popup: 'rounded-xl shadow-lg',
    title: 'text-lg font-semibold',
    confirmButton: 'px-5 py-2'
  }
});

  return;
}

  result.textContent = "⏳ Testing…";
  result.className = "text-yellow-400 font-semibold";

  try {
    let params = new URLSearchParams({ ip, method });
    if (method === 'snmp') {
      const community = $("input[name='community']")?.value || '';
      const port = $("input[name='port']")?.value || '';
      const template = $("select[name='template']")?.value || '';
      params.set('community', community);
      params.set('port', port);
      params.set('template', template);
    }
    const url = `${API}/device_status?${params.toString()}`;
    const res = await fetch(url);
    const data = await res.json();
    const ok = data.status === "online";
    result.textContent = ok ? "Success ✓" : "Offline ✗";
    result.className = ok ? "text-green-400 font-semibold" : "text-red-400 font-semibold";
  } catch (err) {
    result.textContent = "Error";
    result.className = "text-red-400 font-semibold";
  } finally {
    setTimeout(() => { result.textContent = "" }, 3000);
  }
}

window.testConnection = testConnection;