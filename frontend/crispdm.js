// Agrega al inicio del archivo:
import { generarTablaHTMLCruda, generarTablaHTML } from './common.js';
// SUBIDA DE CSV
const fileInput = document.getElementById("inputCsv");
const btnUpload = document.getElementById("btnUpload");

if (fileInput && btnUpload) {
  btnUpload.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    const file = fileInput.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    fetch("https://habilis2025-production.up.railway.app/proceso-csv", {
      method: "POST",
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      const resumen = data.resumen;
      const antes = data.preview_antes;
      const despues = data.preview_despues;

      function setTextoSiExiste(id, texto) {
        const el = document.getElementById(id);
        if (el) el.textContent = texto;
      }

      function setTablaSiExiste(id, html) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
      }

      setTextoSiExiste("prep-total", resumen.originales);
      setTextoSiExiste("prep-eliminados", resumen.eliminados);
      setTextoSiExiste("prep-finales", resumen.finales);
      setTextoSiExiste("prep-salario-ok", resumen.transformaciones_salario);
      setTextoSiExiste("prep-rellenos", resumen.rellenos.join(", "));
      setTextoSiExiste("prep-columnas-eliminadas", resumen.columnas_eliminadas.join(", "));
      setTextoSiExiste("prep-limpieza", resumen.caracteres_limpiados ? "Sí" : "No");
      setTextoSiExiste("prep-habilidades", resumen.habilidades.join(", "));

      setTablaSiExiste("tabla-antes", generarTablaHTMLCruda(antes));
      setTablaSiExiste("tabla-despues", generarTablaHTML(despues));

      alert("Archivo CSV cargado correctamente. Puedes volver al Dashboard.");
    })
    .catch(() => alert("Error al subir el archivo"));
  });
}

fetch("https://habilis2025-production.up.railway.app/registros-eliminados")
  .then(res => res.json())
  .then(data => {
    renderTablaDesdeObjeto(data.no_ingenieria, "tabla-no-ingenieria");
    renderTablaDesdeObjeto(data.no_clasificados, "tabla-no-clasificados");
  });

function renderTablaDesdeObjeto(datos, tablaId) {
  if (!Array.isArray(datos) || datos.length === 0) return;

  const tabla = document.getElementById(tablaId);
  const columnas = Object.keys(datos[0]);

  // Crear encabezado
  tabla.innerHTML = `
    <thead>
      <tr>${columnas.map(col => `<th>${col}</th>`).join('')}</tr>
    </thead>
    <tbody>
      ${datos.map(row =>
        `<tr>${columnas.map(col => `<td>${row[col]}</td>`).join('')}</tr>`
      ).join('')}
    </tbody>
  `;
}
