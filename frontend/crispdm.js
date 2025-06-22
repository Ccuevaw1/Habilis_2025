// Agrega al inicio del archivo:
import { generarTablaHTMLCruda, generarTablaHTML } from './common.js';
// SUBIDA DE CSV
const fileInput = document.getElementById("inputCsv");
const btnUpload = document.getElementById("btnUpload");

// if (fileInput && btnUpload) {
//   btnUpload.addEventListener("click", () => fileInput.click());

//   fileInput.addEventListener("change", () => {
//     const file = fileInput.files[0];
//     if (!file) return;

//     const formData = new FormData();
//     formData.append("file", file);

//     fetch("https://habilis2025-production.up.railway.app/proceso-csv", {
//       method: "POST",
//       body: formData
//     })
//     .then(res => res.json())
//     .then(data => {
//       const resumen = data.resumen;
//       const antes = data.preview_antes;
//       const despues = data.preview_despues;

//       function setTextoSiExiste(id, texto) {
//         const el = document.getElementById(id);
//         if (el) el.textContent = texto;
//       }

//       function setTablaSiExiste(id, html) {
//         const el = document.getElementById(id);
//         if (el) el.innerHTML = html;
//       }

//       setTextoSiExiste("prep-total", resumen.originales);
//       setTextoSiExiste("prep-eliminados", resumen.eliminados);
//       setTextoSiExiste("prep-finales", resumen.finales);
//       setTextoSiExiste("prep-salario-ok", resumen.transformaciones_salario);
//       setTextoSiExiste("prep-rellenos", resumen.rellenos.join(", "));
//       setTextoSiExiste("prep-columnas-eliminadas", resumen.columnas_eliminadas.join(", "));
//       setTextoSiExiste("prep-limpieza", resumen.caracteres_limpiados ? "Sí" : "No");
//       setTextoSiExiste("prep-habilidades", resumen.habilidades.join(", "));

//       setTablaSiExiste("tabla-antes", generarTablaHTMLCruda(antes));
//       setTablaSiExiste("tabla-despues", generarTablaHTML(despues));

//       alert("Archivo CSV cargado correctamente. Puedes volver al Dashboard.");
//     })
//     .catch(() => alert("Error al subir el archivo"));
//   });
// }

// Deshabilitar botón de procesar inicialmente
const btnProcesar = document.getElementById("btnProcesar");
btnProcesar.disabled = true;

// Lógica para subir el CSV
document.getElementById("btnUpload").addEventListener("click", () => {
  document.getElementById("inputCsv").click();
});

document.getElementById("inputCsv").addEventListener("change", async function () {
  const file = this.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("https://habilis2025-production.up.railway.app/proceso-csv", {
      method: "POST",
      body: formData
    });

    if (!response.ok) {
      alert("Error al subir archivo.");
      return;
    }

    const data = await response.json();
    alert("✅ CSV cargado correctamente. ¡Listo para procesar!");

// Guardamos los datos globalmente para usarlos despuésAdd commentMore actions
    window.datosProcesados = data;

    // Habilitamos el botón
    btnProcesar.disabled = false;

  } catch (error) {
    console.error("Error al subir CSV:", error);
    alert("❌ Ocurrió un error al procesar el archivo.");
  }
});

// Mostrar resultados solo al hacer clic en "Procesar"
btnProcesar.addEventListener("click", () => {
  if (!window.datosProcesados) return;

  const datos = window.datosProcesados;

  document.getElementById("preparacion-datos-container").style.display = "block";
  document.getElementById("preview-modelado-container").style.display = "block";
  document.getElementById("precision-container").style.display = "block";

  if (document.getElementById("no-ingenieria-container")) {
    document.getElementById("no-ingenieria-container").style.display = "block";
  }
  if (document.getElementById("no-clasificados-container")) {
    document.getElementById("no-clasificados-container").style.display = "block";
  }

  // Resumen
  document.getElementById("prep-total").textContent = datos.resumen.originales;
  document.getElementById("prep-eliminados").textContent = datos.resumen.eliminados;
  document.getElementById("prep-finales").textContent = datos.resumen.finales;
  document.getElementById("prep-salario-ok").textContent = datos.resumen.transformaciones_salario;
  document.getElementById("prep-rellenos").textContent = datos.resumen.rellenos.join(', ');
  document.getElementById("prep-columnas-eliminadas").textContent = datos.resumen.columnas_eliminadas.join(', ');
  document.getElementById("prep-limpieza").textContent = datos.resumen.caracteres_limpiados ? "Sí" : "No";
  document.getElementById("prep-habilidades").textContent = datos.resumen.habilidades.length;

  // 👉 AQUÍ los generadores de tablas buenos
  document.getElementById("tabla-antes").innerHTML = generarTablaHTMLCruda(datos.preview_antes);
  document.getElementById("tabla-despues").innerHTML = generarTablaHTML(datos.preview_despues);

  if (datos.no_ingenieria) renderTabla("tabla-no-ingenieria", datos.no_ingenieria);
  if (datos.no_clasificados) renderTabla("tabla-no-clasificados", datos.no_clasificados);

  fetch("https://habilis2025-production.up.railway.app/precision-mineria")
    .then(r => r.json())
    .then(d => {
      document.getElementById("precision-modelo").textContent = d.precision ? (d.precision * 100).toFixed(2) + "%" : "⚠️ No evaluado aún";
    });
});

// Función para renderizar tabla
function renderTabla(idTabla, datos) {
  const tabla = document.getElementById(idTabla);
  tabla.innerHTML = "";

  if (datos.length === 0) {
    tabla.innerHTML = "<tr><td>No hay registros</td></tr>";
    return;
  }

  // Crear encabezados
  const headers = Object.keys(datos[0]);
  let thead = "<thead><tr>" + headers.map(h => `<th>${h}</th>`).join('') + "</tr></thead>";

  // Crear filas
  let tbody = "<tbody>";
  for (const fila of datos) {
    tbody += "<tr>" + headers.map(h => `<td>${fila[h]}</td>`).join('') + "</tr>";
  }
  tbody += "</tbody>";

  tabla.innerHTML = thead + tbody;
}



// fetch("https://habilis2025-production.up.railway.app/registros-eliminados")
//   .then(res => res.json())
//   .then(data => {
//     renderTablaDesdeObjeto(data.no_ingenieria, "tabla-no-ingenieria");
//     renderTablaDesdeObjeto(data.no_clasificados, "tabla-no-clasificados");
//   });

// function renderTablaDesdeObjeto(datos, tablaId) {
//   if (!Array.isArray(datos) || datos.length === 0) return;

//   const tabla = document.getElementById(tablaId);
//   const columnas = Object.keys(datos[0]);

//   // Crear encabezado
//   tabla.innerHTML = `
//     <thead>
//       <tr>${columnas.map(col => `<th>${col}</th>`).join('')}</tr>
//     </thead>
//     <tbody>
//       ${datos.map(row =>
//         `<tr>${columnas.map(col => `<td>${row[col]}</td>`).join('')}</tr>`
//       ).join('')}
//     </tbody>
//   `;
// }
