
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

    // Nota: la exportación de Maestros, Escuelas y FUP se maneja en cada
    // plantilla, porque cada una conoce su propia tabla y filtros.

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
