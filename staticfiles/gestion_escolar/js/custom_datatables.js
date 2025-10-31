
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


    // Inicializar la tabla de Maestros con Server-Side Processing
    if ($('#tablaMaestros').length) {
        $('#tablaMaestros').DataTable({
            processing: true,
            serverSide: true,
            ajax: {
                url: $('#tablaMaestros').data('ajax-url'),
                type: 'GET'
            },
            columns: [
                { data: 0 }, // ID
                { data: 1 }, // Nombre
                { data: 2 }, // CCT
                { data: 3 }, // CURP
                { data: 4 }, // Clave Presupuestal
                { data: 5 }, // Status
                { data: 6, orderable: false, searchable: false }, // Acciones
                { data: 7, visible: false } // is_misplaced flag
            ],
            createdRow: function(row, data, dataIndex) {
                // Si el flag is_misplaced es true, añade la clase a la fila
                if (data[7]) {
                    $(row).addClass('text-danger');
                }
            },
            language: {
                url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json',
                processing: `
                    <div class="d-flex justify-content-center">
                        <div class="spinner-border text-primary" role="status"><span class="visually-hidden">Cargando...</span></div>
                    </div>`
            },
            "columnDefs": [
                { "type": "html-accent-neutral", "targets": "_all" }
            ]
        });
    }

    // Inicializar otras tablas que puedan existir con la configuración simple
    $('.datatable-search:not(#tablaMaestros)').DataTable({
        language: {
            url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
        },
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

    // Also, ensure the input field itself converts to uppercase on keyup
    $(document).on('keyup', '.dataTables_filter input', function() {
        var input = $(this);
        var start = input.prop('selectionStart');
        var end = input.prop('selectionEnd');
        input.val(input.val().toUpperCase());
        input.prop('selectionStart', start);
        input.prop('selectionEnd', end);
    });
});
