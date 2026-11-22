"""Server-side DataTables for Django admin lists.

Add `DataTablesAdminMixin` to a ModelAdmin to replace its result table with
a DataTables table that loads one page at a time from `<changelist>/datatable/`.
Everything else keeps working because the JSON is built by Django's own
ChangeList: list_display columns and links, search_fields, list_filter
(the filter sidebar), default ordering and bulk actions (checkbox column).

Not for admins with list_editable (those post a formset of all rows).
"""

import re

from django.contrib.admin.templatetags.admin_list import items_for_result
from django.contrib.admin.views.main import ORDER_VAR, PAGE_VAR, SEARCH_VAR
from django.http import JsonResponse
from django.urls import path

_CELL = re.compile(r"^<(td|th)[^>]*>(.*)</\1>$", re.DOTALL)
_DT_PARAMS = re.compile(r"^(draw|start|length|search\[|order\[|columns\[|_$)")


class DataTablesAdminMixin:
    change_list_template = "admin/datatables_change_list.html"
    datatables_page_lengths = (25, 50, 100)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        custom = [
            path("datatable/", self.admin_site.admin_view(self.datatable_view), name="%s_%s_datatable" % info),
        ]
        return custom + super().get_urls()

    def datatable_view(self, request):
        """JSON for DataTables: {draw, recordsTotal, recordsFiltered, data: [[cell html, …], …]}."""
        params = request.GET.copy()
        draw = int(params.get("draw") or 0)
        start = max(0, int(params.get("start") or 0))
        length = min(200, max(1, int(params.get("length") or self.datatables_page_lengths[0])))
        search = params.get("search[value]", "").strip()
        order_col = params.get("order[0][column]")
        order_dir = params.get("order[0][dir]", "asc")

        # Hand DataTables' search / sort to Django's ChangeList (it understands q and o).
        for key in list(params.keys()):
            if _DT_PARAMS.match(key):
                del params[key]
        params.pop(PAGE_VAR, None)
        if search:
            params[SEARCH_VAR] = search
        if order_col not in (None, ""):
            params[ORDER_VAR] = ("-" if order_dir == "desc" else "") + str(int(order_col))
        request.GET = params

        cl = self.get_changelist_instance(request)
        queryset = cl.queryset
        rows = list(queryset[start:start + length])
        cl.result_list = rows
        cl.formset = None

        data = []
        for obj in rows:
            cells = []
            for cell in items_for_result(cl, obj, None):
                match = _CELL.match(str(cell).strip())
                cells.append(match.group(2) if match else str(cell))
            data.append(cells)

        return JsonResponse({
            "draw": draw,
            "recordsTotal": cl.root_queryset.count(),
            "recordsFiltered": queryset.count(),
            "data": data,
        })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        info = self.model._meta.app_label, self.model._meta.model_name
        extra_context.setdefault("datatable_url_name", "admin:%s_%s_datatable" % info)
        extra_context.setdefault("datatables_page_lengths", list(self.datatables_page_lengths))
        return super().changelist_view(request, extra_context)
