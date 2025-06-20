
const API_URL = 'https://habilis2025-production.up.railway.app/estadisticas/habilidades';
const API_SALARIOS = 'https://habilis2025-production.up.railway.app/estadisticas/salarios';
const selectCarrera = document.getElementById('select-carrera');
const tituloCarrera = document.getElementById('titulo-carrera');

const graficoTecnicas = new Chart(document.getElementById('graficoTecnicas'), {
  type: 'bar',
  data: { labels: [], datasets: [{ label: 'Frecuencia', data: [], backgroundColor: '#4e73df' }] },
  options: { indexAxis: 'y' }
});

const graficoBlandas = new Chart(document.getElementById('graficoBlandas'), {
  type: 'bar',
  data: { labels: [], datasets: [{ label: 'Frecuencia', data: [], backgroundColor: '#1cc88a' }] },
  options: { indexAxis: 'y' }
});

selectCarrera.addEventListener('change', () => {
  const inicioTiempo = Date.now(); // tiempo seleccionar carrera en segundos
  const carrera = selectCarrera.value;
  tituloCarrera.textContent = carrera.toUpperCase();
  fetch(`${API_URL}?carrera=${encodeURIComponent(carrera)}`)
    .then(res => res.json())
    .then(data => {
      const topTecnicas = data.habilidades_tecnicas.slice(0, 5);
      const topBlandas = data.habilidades_blandas.slice(0, 5);

      graficoTecnicas.data.labels = topTecnicas.map(h => h.nombre);
      graficoTecnicas.data.datasets[0].data = topTecnicas.map(h => h.frecuencia);
      graficoTecnicas.update();

      graficoBlandas.data.labels = topBlandas.map(h => h.nombre);
      graficoBlandas.data.datasets[0].data = topBlandas.map(h => h.frecuencia);
      graficoBlandas.update();

      document.querySelector('#tabla-blandas tbody').innerHTML = topBlandas.map((h, i) =>
        `<tr><td>${i+1}</td><td>${h.nombre}</td><td>${h.frecuencia}</td></tr>`).join('');

      document.querySelector('#tabla-tecnicas tbody').innerHTML = topTecnicas.map((h, i) =>
        `<tr><td>${i+1}</td><td>${h.nombre}</td><td>${h.frecuencia}</td></tr>`).join('');
    });

  // Nuevo fetch para los salarios
  fetch(`${API_SALARIOS}?carrera=${encodeURIComponent(carrera)}`)
  .then(res => res.json())
  .then(data => {
    const salarios = data.salarios || [];
    const puestos = salarios.map(s => s.puesto.length > 40 ? s.puesto.slice(0, 37) + '...' : s.puesto);
    const valores = salarios.map(s => s.salario);

    if (window.graficoSalariosInstance) {
      window.graficoSalariosInstance.destroy();
    }

    const ctx = document.getElementById('graficoSalarios').getContext('2d');
    window.graficoSalariosInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: puestos,
        datasets: [{
          label: 'Salario (S/)',
          data: valores,
          backgroundColor: 'rgba(72, 191, 145, 0.8)', // tono verde profesional
          borderColor: '#48bf91',
          borderWidth: 1
        }]
      },
      options: {
        indexAxis: 'y', // BARRAS HORIZONTALES
        responsive: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `S/ ${ctx.raw.toLocaleString()}`
            }
          },
          title: {
            display: false
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              callback: value => `S/ ${value.toLocaleString()}`
            },
            title: {
              display: true,
              text: "Salario en soles (S/)",
              color: "#333",
              font: { size: 14, weight: "bold" }
            }
          },
          y: {
            ticks: {
              color: "#333",
              font: { size: 12 }
            }
          }
        }
      }
    });
    const finTiempo = Date.now();
    fetch(`https://habilis2025-production.up.railway.app/tiempo-carga/?carrera=${encodeURIComponent(carrera)}&inicio=${inicioTiempo/1000}`, {
      method: "POST"
      })
    .then(res => res.json())
    .then(data => console.log(data.mensaje))
    .catch(err => console.warn("No se pudo registrar el tiempo:", err));
  });
});

// Exportar sin mostrar el botón
document.getElementById('btnExportar').addEventListener('click', () => {
  const contenedor = document.getElementById('contenedor-pdf');
  const carrera = selectCarrera.value || 'ingenieria'; // fallback
  const año = new Date().getFullYear();

  // limpiar texto: minúsculas, sin tildes, guiones bajos
  const carreraFormateada = carrera
    .toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "") // quita tildes
    .replace(/\s+/g, "_"); // reemplaza espacios por guiones bajos

  const nombreArchivo = `habilidades_${carreraFormateada}_${año}.pdf`;

  const opciones = {
    margin: 0.3,
    filename: nombreArchivo,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
  };

  html2pdf().set(opciones).from(contenedor).save();
});
//-----------------------------------------
const fileInput = document.getElementById("inputCsv");
const btnUpload = document.getElementById("btnUpload");

// Cuando haces clic en el botón, se abre el input de archivo
btnUpload.addEventListener("click", () => {
  fileInput.click();
});

// Cuando eliges un archivo, se sube automáticamente
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

    alert("Archivo CSV cargado correctamente!");
  })
  .catch(() => alert("Error al subir el archivo, no cumple con la estructura proporcionada por Octoparse."));
});

function generarTablaHTMLCruda(data) {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return '<p class="error">No hay datos crudos disponibles</p>';
  }

  try {
    // Obtener TODAS las columnas del primer registro
    const columnas = Object.keys(data[0]);
    
    // Crear tabla
    const thead = `<thead><tr>${columnas.map(col => `<th>${col}</th>`).join('')}</tr></thead>`;

      const tbody = `<tbody>${data.map(row => {
        return `<tr>${
          columnas.map(col => {
            const value = row[col];
            // Limitar el largo del texto para mejor visualización
            const text = value !== null && value !== undefined ? String(value) : '-';
            return `<td title="${text}">${text.length > 30 ? text.substring(0, 27) + '...' : text}</td>`;
          }).join('')
        }</tr>`;
      }).join('')}</tbody>`;
    return `<table class="tabla-estilo">${thead}${tbody}</table>`;
  } catch (error) {
    console.error('Error generando tabla cruda:', error);
    return `<p class="error">Error mostrando datos: ${error.message}</p>`;
  }
}

function generarTablaHTML(data) {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return '<p class="error">No hay datos disponibles</p>';
  }

  try {
    // 1. Columnas base que siempre mostramos
    const columnasBase = ["career", "title", "company", "workday", "modality", "salary"];
    
    // 2. Función para formatear nombres de columnas
    const formatearNombreColumna = (col) => {
      if (columnasBase.includes(col)) return col;
      return col.replace(/^(hard|soft)_/, '')  // Quita prefijo
               .replace(/_/g, ' ')            // Reemplaza guiones bajos
               .replace(/\b\w/g, l => l.toUpperCase()); // Capitaliza
    };

    // 3. Función para truncar texto con tooltip
    const truncarTexto = (text, maxLength = 30) => {
      const str = text !== null && text !== undefined ? String(text) : '-';
      return {
        display: str.length > maxLength ? str.substring(0, maxLength-3) + '...' : str,
        full: str
      };
    };

    // 4. Encontrar columnas de habilidades con al menos un 1 (TRUE)
    const columnasHabilidadesActivas = Object.keys(data[0])
      .filter(col => (col.startsWith("hard_") || col.startsWith("soft_")) && 
             data.some(row => {
               const val = row[col];
               return val === 1 || val === true || val === "true" || val === "TRUE";
             }));

    // 5. Generar estructura de la tabla
    let html = '<table class="tabla-estilo tabla-procesada"><thead><tr>';
    
    // Encabezados para columnas base
    html += columnasBase.map(col => `<th>${formatearNombreColumna(col)}</th>`).join('');
    
    // Encabezados para habilidades activas
    html += columnasHabilidadesActivas.map(col => `<th>${formatearNombreColumna(col)}</th>`).join('');
    html += '</tr></thead><tbody>';

    // Filas de datos
    html += data.map(row => {
      let fila = '<tr>';
      
      // Columnas base con texto truncado
      fila += columnasBase.map(col => {
        const {display, full} = truncarTexto(row[col]);
        return `<td title="${escapeHtml(full)}">${escapeHtml(display)}</td>`;
      }).join('');
      
      // Columnas de habilidades (mostrar 1 o 0)
      fila += columnasHabilidadesActivas.map(col => {
        const val = row[col];
        const isActive = val === 1 || val === true || val === "true" || val === "TRUE";
        return `<td class="centrado">${isActive ? '1' : '0'}</td>`;
      }).join('');
      
      return fila + '</tr>';
    }).join('');

    return html + '</tbody></table>';
  } catch (error) {
    console.error('Error generando tabla:', error);
    return `<p class="error">Error mostrando datos: ${escapeHtml(error.message)}</p>`;
  }
}

// Función de escape HTML (añadir si no existe)
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  return text.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
} 

const inputManual = document.getElementById("inputManualCsv");
const btnVerificar = document.getElementById("btnVerificar");

btnVerificar.addEventListener("click", () => {
  inputManual.click();
});

inputManual.addEventListener("change", () => {
  const file = inputManual.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("file", file);

  fetch("https://habilis2025-production.up.railway.app/verificar-modelo/", {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      alert(data.mensaje || "Precisión calculada.");

      document.getElementById("eval-precision").textContent = 
        (data.precision * 100).toFixed(2) + "%" || "N/A";
      document.getElementById("eval-recall").textContent = 
        (data.recall * 100).toFixed(2) + "%" || "N/A";
      document.getElementById("eval-cobertura").textContent = 
        data.cobertura_media?.toFixed(2) || "N/A";
      document.getElementById("eval-ruidosas").textContent = Object.entries(data.habilidades_ruidosas || {})
        .map(([h, v]) => `${h.replace(/^(hard|soft)_/, '')} (${(v * 100).toFixed(1)}%)`).join(", ");
    })
    .catch(() => alert("Error al verificar el modelo."));
});

fetch("https://habilis2025-production.up.railway.app/precision-mineria/")
  .then(res => res.json())
  .then(data => {
    const precisionText = data.mensaje || `Precisión del modelo de minería: ${(data.precision * 100).toFixed(2)}%`;
    document.getElementById('precision-modelo').innerText = precisionText;
  })
  .catch(() => {
    document.getElementById('precision-modelo').innerText = "No se pudo cargar la precisión del modelo.";
  });

