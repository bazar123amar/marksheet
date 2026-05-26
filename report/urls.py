from django.urls import path
from .views import  upload_excel, download_pdf, student_report, download_all_reports

urlpatterns = [

    

    path(
        "",
        upload_excel,
        name="upload_excel"
    ),

    path(
    "download/",
    download_pdf,
    name="download_pdf"
    ),

    path(
        "report/<int:roll>/",
         student_report,
        name="student_report"
    ),

    path(
        "download-all/",
        download_all_reports,
        name="download_all_reports"
    ),

]