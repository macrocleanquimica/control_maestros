
$(document).ready(function() {
    // Función para normalizar texto (quitar acentos)
    var accent_normalize = function(data) {
        if (typeof data !== 'string') {
            return data;
        }
        return data.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    };

    // Registrar la función de búsqueda para strings y html
    $.fn.dataTable.ext.type.search['string-accent-neutral'] = accent_normalize;
    $.fn.dataTable.ext.type.search['html-accent-neutral'] = accent_normalize;

    // Inicializar todas las tablas que tengan la clase 'datatable-search'
    $('.datatable-search').DataTable({
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
        },
        // Aplicar la búsqueda sin acentos a todas las columnas
        "columnDefs": [
            { "type": "html-accent-neutral", "targets": "_all" }
        ]
    });

    // Lógica para el botón de exportar a Excel
    $('#export-excel-btn').on('click', function() {
        // Obtener la instancia de la tabla específica por su ID
        var tablaMaestros_instance = $('#tablaMaestros').DataTable();
        
        // Obtener el valor actual del campo de búsqueda de esa instancia
        var filtro = tablaMaestros_instance.search();

        // Construir la URL para la exportación
        var url = '/maestros/exportar/excel/?filtro=' + encodeURIComponent(filtro);

        // Redirigir para iniciar la descarga
        window.location.href = url;
    });
});
