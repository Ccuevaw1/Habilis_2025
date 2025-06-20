// CONSTANTES COMPARTIDAS
const API_URL = 'https://habilis2025-production.up.railway.app/estadisticas/habilidades';
const API_SALARIOS = 'https://habilis2025-production.up.railway.app/estadisticas/salarios';

// FUNCIONES UTILITARIAS
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  return text.toString()
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

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

// FUNCIONES DE API
async function subirCSV(file) {
  const formData = new FormData();
  formData.append("file", file);
  
  const response = await fetch("https://habilis2025-production.up.railway.app/proceso-csv", {
    method: "POST",
    body: formData
  });
  
  if (!response.ok) throw new Error("Error en la subida");
  return await response.json();
}

// // FUNCIÓN PARA MEDIR Y REGISTRAR TIEMPOS
// export async function registrarTiempoCarga(carrera, inicioTiempo) {
//   const finTiempo = Date.now();
//   const tiempoTotal = (finTiempo - inicioTiempo) / 1000;
  
//   console.log(`[DEBUG] Tiempo de identificación: ${tiempoTotal.toFixed(4)} segundos`);
  
//   try {
//     const response = await fetch(`https://habilis2025-production.up.railway.app/tiempo-carga/?carrera=${encodeURIComponent(carrera)}&inicio=${inicioTiempo/1000}`, {
//       method: "POST"
//     });
//     return await response.json();
//   } catch (error) {
//     console.error("Error registrando tiempo:", error);
//     return { error: true };
//   }
// }