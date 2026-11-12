
$(document).ready(function () {
    // Función para normalizar texto (quitar acentos)
    var accent_normalize = function (data) {
        if (typeof data !== 'string') {
            return data;
        }
        return data.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    };

    // Envolver las funciones de búsqueda de texto para que ignoren acentos.
    // Los tipos numéricos y de fecha no pasan por aquí, así que su
    // ordenamiento y búsqueda siguen intactos.
    if ($.fn.dataTable) {
        var busquedaString = $.fn.dataTable.ext.type.search.string;
        var busquedaHtml = $.fn.dataTable.ext.type.search.html;

        $.fn.dataTable.ext.type.search.string = function (data) {
            return accent_normalize(busquedaString(data));
        };
        $.fn.dataTable.ext.type.search.html = function (data) {
            return accent_normalize(busquedaHtml(data));
        };
    }

    // Configuración común para todas las DataTables del sistema.
    // Así el buscador, la paginación, el tamaño de página y los estados
    // vacíos se ven igual en todas las pantallas.
    if ($.fn.dataTable && window.SpanishDataTable) {
        $.extend(true, $.fn.dataTable.defaults, {
            language: $.extend({}, window.SpanishDataTable, {
                search: "_INPUT_",
                emptyTable: '<div class="comp-empty-state">' +
                    '<i class="fas fa-inbox"></i>' +
                    '<p>No hay registros disponibles.</p>' +
                    '</div>',
                zeroRecords: '<div class="comp-empty-state">' +
                    '<i class="fas fa-search"></i>' +
                    '<p>No se encontraron resultados.</p>' +
                    '</div>'
            }),
            pageLength: 25,
            lengthMenu: [10, 25, 50, 100],
            autoWidth: false,
            searchDelay: 300,
            dom: '<"d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3"lf>rt<"d-flex flex-wrap justify-content-between align-items-center gap-2 mt-3"ip>'
        });
    }

    // Normalizar también el texto que escribe el usuario, para que la
    // búsqueda sin acentos funcione en todas las tablas.
    if ($.fn.dataTable) {
        $(document).on('init.dt', function (evento, settings) {
            if (!settings || !settings.nTableWrapper) {
                return;
            }
            var api = new $.fn.dataTable.Api(settings);
            var input = $(settings.nTableWrapper).find('.dataTables_filter input');
            var temporizador;

            input.off().on('input search keyup', function () {
                var valor = accent_normalize(this.value);
                clearTimeout(temporizador);
                temporizador = setTimeout(function () {
                    api.search(valor).draw();
                }, 250);
            });
        });
    }

    // Inicializar tablas con la configuración global de idioma
    $('.datatable-search').each(function () {
        if (!$.fn.DataTable.isDataTable(this)) {
            $(this).DataTable();
        }
    });

    // Nota: la exportación de Maestros, Escuelas y FUP se maneja en cada
    // plantilla, porque cada una conoce su propia tabla y filtros.
});
