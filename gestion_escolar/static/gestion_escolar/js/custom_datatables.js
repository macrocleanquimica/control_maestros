
$(document).ready(function () {
    // Función para normalizar texto (quitar acentos)
    var accent_normalize = function (data) {
        if (typeof data !== 'string') {
            return data;
        }
        return data.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    };

    // Registrar la función de búsqueda para strings y html
    $.fn.dataTable.ext.type.search['string-accent-neutral'] = accent_normalize;
    $.fn.dataTable.ext.type.search['html-accent-neutral'] = accent_normalize;


    // Inicializar tablas con la configuración global de idioma
    $('.datatable-search').each(function () {
        if (!$.fn.DataTable.isDataTable(this)) {
            $(this).DataTable({
                language: {
                    ...window.SpanishDataTable,
                    search: "_INPUT_"
                },
                "columnDefs": [
                    { "type": "html-accent-neutral", "targets": "_all" }
                ]
            });
        }
    });

    // Lógica para el botón de exportar a Excel de Maestros
    $('#export-excel-btn').on('click', function () {
        var tablaMaestros_instance = $('#tablaMaestros').DataTable();
        var filtro = tablaMaestros_instance.search();
        var url = '/maestros/exportar/excel/?filtro=' + encodeURIComponent(filtro);
        window.location.href = url;
    });

    // Lógica para el botón de exportar a Excel de FUPs
    $('#export-excel-fup-btn').on('click', function () {
        var tablaFUPs_instance = $('#tablaFUPs').DataTable();
        var filtro = tablaFUPs_instance.search();
        var url = '/fup/exportar/excel/?filtro=' + encodeURIComponent(filtro);
        window.location.href = url;
    });

    // Lógica para el botón de exportar a Excel de Escuelas
    $(document).on('click', '#export-excel-escuelas-btn', function () {
        console.log('Botón exportar escuelas clickeado');
        var tablaEscuelas_instance = $('#tablaEscuelas').DataTable();
        var filtro = tablaEscuelas_instance.search();
        console.log('Filtro actual:', filtro);
        var url = '/escuelas/exportar/excel/?filtro=' + encodeURIComponent(filtro);
        window.location.href = url;
    });

    // Also, ensure the input field itself converts to uppercase on keyup
    $(document).on('keyup', '.dataTables_filter input', function () {
        var input = $(this);
        var start = input.prop('selectionStart');
        var end = input.prop('selectionEnd');
        input.val(input.val().toUpperCase());
        input.prop('selectionStart', start);
        input.prop('selectionEnd', end);
    });
});
