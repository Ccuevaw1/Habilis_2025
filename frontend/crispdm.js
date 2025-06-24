// Agrega al inicio del archivo:
import { generarTablaHTMLCruda, generarTablaHTML } from './common.js';
// SUBIDA DE CSV
const fileInput = document.getElementById("inputCsv");
const btnUpload = document.getElementById("btnUpload");

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

    // Guardamos los datos globalmente para usarlos después
    window.datosProcesados = data;

    btnProcesar.disabled = false;
    //document.getElementById("btnVerificar").style.display = "inline-block";

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
  document.getElementById("no-ingenieria-container").style.display = "block";

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

  if (datos.no_ingenieria && datos.no_ingenieria.length > 0) {
    renderTabla("tabla-no-ingenieria", datos.no_ingenieria);
  } else {
    document.getElementById("tabla-no-ingenieria").innerHTML = "<tr><td>No hay registros no relacionados a ingeniería</td></tr>";
  }

  if (datos.no_clasificados && datos.no_clasificados.length > 0) {
    renderTabla("tabla-no-clasificados", datos.no_clasificados);
  } else {
    document.getElementById("tabla-no-clasificados").innerHTML = "<tr><td>No hay registros no clasificados</td></tr>";
  }

  // Mostrar evaluación por carrera
  document.getElementById("evaluacion-container").style.display = "block";

  // Fetch a evaluación-modelo
  fetch("https://habilis2025-production.up.railway.app/evaluacion-modelo")
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        document.getElementById("tabla-resumen-carreras").innerHTML = `<tr><td>${data.error}</td></tr>`;
        return;
      }

      // 🟢 Resumen por carrera
      const resumen = data.resumen_por_carrera;
      let htmlResumen = `
        <thead><tr><th>Carrera</th><th>Registros</th><th>Porcentaje</th></tr></thead>
        <tbody>
          ${resumen.map(row => `
            <tr>
              <td>${row.carrera}</td>
              <td>${row.registros}</td>
              <td>${row.porcentaje}%</td>
            </tr>
          `).join('')}
        </tbody>
      `;
      document.getElementById("tabla-resumen-carreras").innerHTML = htmlResumen;

      // 🟢 Tablas por carrera
      const detalle = data.detalle_por_carrera;
      let htmlDetalles = "";
      for (const carrera in detalle) {
        const idTabla = `tabla-${carrera.replace(/\s+/g, '-').toLowerCase()}`;
        htmlDetalles += `
          <div class="tabla-seccion">
            <h4>${carrera}</h4>
            <div class="tabla-scroll-container">
              <table class="tabla-estilo tabla-procesados" id="${idTabla}"></table>
            </div>
          </div>
        `;
      }
      document.getElementById("tablas-detalle-carreras").innerHTML = htmlDetalles;

      // 🟢 Render cada tabla con función existente
      for (const carrera in detalle) {
        const idTabla = `tabla-${carrera.replace(/\s+/g, '-').toLowerCase()}`;
        renderTabla(idTabla, detalle[carrera]);
      }
    })
    .catch(err => {
      console.error("Error al cargar evaluación:", err);
      document.getElementById("tabla-resumen-carreras").innerHTML = `<tr><td>Error al obtener datos de evaluación</td></tr>`;
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

