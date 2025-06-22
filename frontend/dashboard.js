import { registrarTiempoCarga } from './common.js';
import { API_URL, API_SALARIOS } from './common.js';
// ELEMENTOS DEL DOM
const selectCarrera = document.getElementById('select-carrera');
const tituloCarrera = document.getElementById('titulo-carrera');

// INICIALIZACIÓN DE GRÁFICOS
if (document.getElementById('graficoTecnicas')) {
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

  // EVENTO PARA CAMBIO DE CARRERA (CON MEDICIÓN DE TIEMPO)
  selectCarrera.addEventListener('change', () => {
    const inicioTiempo = Date.now();
    const carrera = selectCarrera.value;
    tituloCarrera.textContent = carrera.toUpperCase();

    // Fetch habilidades
    fetch(`${API_URL}?carrera=${encodeURIComponent(carrera)}`)
      .then(res => res.json())
      .then(data => {
        const topTecnicas = data.habilidades_tecnicas.slice(0, 5);
        const topBlandas = data.habilidades_blandas.slice(0, 5);

        // Actualizar gráficos
        graficoTecnicas.data.labels = topTecnicas.map(h => h.nombre);
        graficoTecnicas.data.datasets[0].data = topTecnicas.map(h => h.frecuencia);
        graficoTecnicas.update();

        graficoBlandas.data.labels = topBlandas.map(h => h.nombre);
        graficoBlandas.data.datasets[0].data = topBlandas.map(h => h.frecuencia);
        graficoBlandas.update();

        // Actualizar tablas
        document.querySelector('#tabla-blandas tbody').innerHTML = topBlandas.map((h, i) =>
          `<tr><td>${i+1}</td><td>${h.nombre}</td><td>${h.frecuencia}</td></tr>`).join('');

        document.querySelector('#tabla-tecnicas tbody').innerHTML = topTecnicas.map((h, i) =>
          `<tr><td>${i+1}</td><td>${h.nombre}</td><td>${h.frecuencia}</td></tr>`).join('');

        // Registrar tiempo de carga
        registrarTiempoCarga(carrera, inicioTiempo)
          .then(data => console.log(data.mensaje))
          .catch(err => console.warn("No se pudo registrar el tiempo:", err));
      });
    

    // Fetch salarios
    fetch(`${API_SALARIOS}?carrera=${encodeURIComponent(carrera)}`)
      .then(res => res.json())
      .then(data => {
        const salarios = data.salarios || [];
        const puestos = salarios.map(s => s.puesto.length > 40 ? s.puesto.slice(0, 37) + '...' : s.puesto);
        const valores = salarios.map(s => s.salario);

        // Destruir gráfico anterior si existe
        if (window.graficoSalariosInstance) {
          window.graficoSalariosInstance.destroy();
        }

        // Crear nuevo gráfico
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
      });
  });
}

// EXPORTAR PDF
if (document.getElementById('btnExportar')) {
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
}