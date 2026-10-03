from django.urls import path
from . import views

urlpatterns = [
    path('', views.ReportsDashboardView.as_view(), name='reports_dashboard'),
    path('export/csv/', views.ExportCSVView.as_view(), name='export_csv'),
    path('export/excel/',
         views.ExportExcelView.as_view(),
         name='export_excel'),
    path('export/pdf/', views.ExportPDFView.as_view(), name='export_pdf'),
    path('import/', views.ImportCSVView.as_view(), name='reports_import'),
    path('import/confirm/',
         views.ImportConfirmView.as_view(),
         name='reports_import_confirm'),
    path('backup/export/',
         views.BackupExportView.as_view(),
         name='backup_export'),
    path('backup/restore/',
         views.BackupRestoreView.as_view(),
         name='backup_restore'),
]
