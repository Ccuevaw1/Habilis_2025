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

    const data = await response.json();
    
    if (!response.ok || data.error) {
      // Mostrar error específico si existe
      let errorMsg = data.message || "Error al procesar el archivo";
      if (data.suggestion) errorMsg += `\n\nSugerencia: ${data.suggestion}`;
      
      alert(errorMsg);
      return;
    }

    // Solo mostrar confirmación si todo está bien
    alert("✅ CSV cargado correctamente. ¡Listo para procesar!");
    window.datosProcesados = data;

    // Mostrar tabla sin procesar al cargar el archivo
    document.getElementById("preview-modelado-container").style.display = "block";
    document.getElementById("tabla-antes").innerHTML = generarTablaHTMLCruda(data.preview_antes);

    // Mover botón "Procesar CSV" debajo de esa tabla
    document.getElementById("seccion-boton-procesar").style.display = "block";


  } catch (error) {
    console.error("Error al subir CSV:", error);
    alert("Error de conexión al procesar el archivo.");
  }
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

// Mostrar resultados solo al hacer clic en "Procesar"
btnProcesar.addEventListener("click", () => {
  if (!window.datosProcesados) return;

  const datos = window.datosProcesados;

  document.getElementById("preparacion-datos-container").style.display = "block";
  document.getElementById("preview-modelado-container").style.display = "block";
  document.getElementById("porcentaje-carreras-container").style.display = "block";

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

  // AQUÍ los generadores de tablas buenos
  document.getElementById("tabla-antes").innerHTML = generarTablaHTMLCruda(datos.preview_antes);
  document.getElementById("tabla-despues").innerHTML = generarTablaHTML(datos.preview_despues);

  // DISTRIBUCIÓN POR CARRERA
  document.getElementById("porcentaje-carreras-container").style.display = "block";

  const registros = datos.preview_despues;
  if (registros && registros.length > 0) {
    const conteoCarreras = {};
    for (const reg of registros) {
      const carrera = reg.career || 'Sin clasificar';
      conteoCarreras[carrera] = (conteoCarreras[carrera] || 0) + 1;
    }

    const total = registros.length;
    const filasHTML = Object.entries(conteoCarreras).map(([carrera, cantidad]) => {
      const porcentaje = ((cantidad / total) * 100).toFixed(1);
      return `<tr>
        <td>${carrera}</td>
        <td>${cantidad}</td>
        <td>${porcentaje}%</td>
      </tr>`;
    });

    document.getElementById("tabla-carreras-porcentaje").innerHTML = `
      <thead>
        <tr><th>Carrera</th><th>Registros</th><th>Porcentaje</th></tr>
      </thead>
      <tbody>${filasHTML.join("")}</tbody>
    `;
  }

  // REGISTROS DETALLADOS POR CARRERA
  document.getElementById("detalles-carrera-container").style.display = "block";

  const agrupados = {};
  for (const reg of registros) {
    const carrera = reg.career || 'Sin clasificar';
    if (!agrupados[carrera]) agrupados[carrera] = [];
    agrupados[carrera].push(reg);
  }

  const contenedor = document.getElementById("tablas-carreras-detalle");
  contenedor.innerHTML = "";  // Limpiar anteriores si los hubiera

  for (const [carrera, filas] of Object.entries(agrupados)) {
    const tablaHTML = generarTablaHTML(filas);  // tabla en formato HTML

    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = `${carrera} (${filas.length} registros)`;
    summary.style.fontWeight = "bold";
    summary.style.margin = "1rem 0";

    details.appendChild(summary);

    const contenedorTabla = document.createElement("div");
    contenedorTabla.innerHTML = tablaHTML;
    contenedorTabla.className = "tabla-seccion";

    details.appendChild(contenedorTabla);
    contenedor.appendChild(details);
  }


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
});
