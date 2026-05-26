import zipfile
import io
from django.shortcuts import render
from .forms import ExcelUploadForm
import pandas as pd
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from weasyprint import HTML
from django.template.loader import render_to_string

from django.http import HttpResponse

from django.contrib.staticfiles import finders
import os
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings
from django.contrib.staticfiles import finders
from xhtml2pdf import pisa
import os


def link_callback(uri, rel):

    if uri.startswith(settings.STATIC_URL):

        path = finders.find(
            uri.replace(
                settings.STATIC_URL,
                ""
            )
        )

        return path

    elif uri.startswith(settings.MEDIA_URL):

        path = os.path.join(
            settings.MEDIA_ROOT,
            uri.replace(
                settings.MEDIA_URL,
                ""
            )
        )

        return path

    return uri


def generate_pdf(request):

    context = request.session.get(
        "report_data"
    )

    template = get_template(
        "report_card.html"
    )

    html = template.render(
        context
    )

    response = HttpResponse(
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = 'filename="report.pdf"'


    pisa_status = pisa.CreatePDF(

        html,

        dest=response,

        link_callback=link_callback

    )

    if pisa_status.err:

        return HttpResponse(
            "PDF generation failed"
        )

    return response


def upload_excel(request):

    form = ExcelUploadForm()

    if request.method == "POST":

        form = ExcelUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            try:

                excel_file = request.FILES["excel_file"]

                # Read Excel
                df = pd.read_excel(
                    excel_file,
                    header=5
                )

                # Remove empty rows
                df = df.dropna(how="all")

                # Rename columns
                df.columns = [

                    "roll",
                    "name",
                    "father",
                    "class_name",
                    "blank",

                    "bangla_w",
                    "bangla_o",

                    "english_w",
                    "english_o",

                    "math_w",
                    "math_o",

                    "arabic_w",
                    "arabic_o",

                    "hindi_w",
                    "hindi_o",

                    "gk_w",
                    "gk_o",

                    "deeniyat_w",
                    "deeniyat_o",

                    "grand_total",
                    "total",
                    "percentage",
                    "rank",
                    "grade"
                ]

                # Save Excel data in session
                request.session["excel_data"] = df.to_dict(
                    orient="records"
                )

                # Student list
                student_list = []

                for _, row in df.iterrows():

                    try:

                        student_list.append({

                            "roll": int(
                                row["roll"]
                            ),

                            "name": str(
                                row["name"]
                            ),

                            "class_name": str(
                                row["class_name"]
                            ),

                            "rank": int(
                                row["rank"]
                            )

                        })

                    except:
                        pass

                # Get roll
                roll = request.POST.get("roll")

                # Show student list
                if not roll:

                    return render(
                        request,
                        "student_list.html",
                        {
                            "students": student_list
                        }
                    )

                # Find student
                student_row = df[
                    df["roll"].astype(str).str.strip()
                    ==
                    str(roll).strip()
                ]

                # Student not found
                if student_row.empty:

                    return render(
                        request,
                        "upload.html",
                        {
                            "form": form,
                            "error": "Student not found"
                        }
                    )

                # First matched student
                student_row = student_row.iloc[0]

                # Student info
                student = {

                    "name": str(
                        student_row["name"]
                    ),

                    "roll": int(
                        student_row["roll"]
                    ),

                    "class_name": str(
                        student_row["class_name"]
                    ),

                    "section": "A",

                    "father": str(
                        student_row["father"]
                    ),

                    "mother": "N/A",

                    "session": "2026",

                    "exam": "1st Term",

                    "photo": None
                }

                # Subject mapping
                subject_map = {

                    "bangla_w": "Bangla",
                    "english_w": "English",
                    "math_w": "Math",
                    "arabic_w": "Arabic",
                    "hindi_w": "Hindi",
                    "gk_w": "GK",
                    "deeniyat_w": "Deeniyat"
                }

                # Subjects
                subjects = []

                for key, name in subject_map.items():

                    written = student_row.get(
                        key,
                        0
                    )

                    oral = student_row.get(
                        key.replace("_w", "_o"),
                        0
                    )

                    # Handle NaN
                    written = 0 if pd.isna(written) else int(written)
                    oral = 0 if pd.isna(oral) else int(oral)

                    obtained = written + oral

                    # Grade
                    grade, gpa = calculate_grade(
                        obtained
                    )

                    subjects.append({

                        "name": name,

                        "full_marks": 50,

                        "obtained": obtained,

                        "grade": grade,

                        "gpa": gpa
                    })

                # Total obtained
                total_obtained = sum(

                    subject["obtained"]

                    for subject in subjects
                )

                # Result
                result = "PASS"

                for subject in subjects:

                    if subject["obtained"] < 17:

                        result = "FAIL"
                        break

                # Final context
                context = {

                    "student": student,

                    "subjects": subjects,

                    "total_full_marks": int(
                        len(subjects) * 50
                    ),

                    "total_obtained": int(
                        total_obtained
                    ),

                    "final_grade": str(
                        student_row["grade"]
                    ),

                    "final_gpa": 5.0,

                    "result": result,

                    "position": int(
                        student_row["rank"]
                    ),

                    "attendance": "95%",

                    "remarks": "Good Performance"
                }

                # Save report
                request.session["report_data"] = context

                return render(
                    request,
                    "report_card.html",
                    context
                )

            except Exception as e:

                return render(
                    request,
                    "upload.html",
                    {
                        "form": form,
                        "error": str(e)
                    }
                )

    return render(
        request,
        "upload.html",
        {
            "form": form
        }
    )


def calculate_grade(mark):

    if mark >= 40:
        return "A+", 5.00

    elif mark >= 35:
        return "A", 4.00

    elif mark >= 30:
        return "A-", 3.50

    elif mark >= 25:
        return "B", 3.00

    elif mark >= 20:
        return "C", 2.00

    elif mark >= 17:
        return "D", 1.00

    else:
        return "F", 0.00
 
def download_pdf(request):
    context = request.session.get("report_data")
    if not context:
        return HttpResponse("No report data found. Please generate report first.")

    html_string = render_to_string("report_pdf.html", context)
    # Build absolute URI for static files
    base_url = request.build_absolute_uri("/")
    pdf_file = HTML(string=html_string, base_url=base_url).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="report_card.pdf"'
    return response


def generate_pdf(request):

    context = request.session["report_data"]

    html_string = render_to_string(
        "report_card.html",
        context
    )

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri()
    ).write_pdf()

    response = HttpResponse(
        pdf,
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ]='filename="report.pdf"'

    return response



def generate_report(
    request,
    student_row
):

    student = {

        "name": str(student_row["name"]),
        "roll": int(student_row["roll"]),
        "class_name": str(student_row["class_name"]),
        "section": "A",
        "father": str(student_row["father"]),
        "mother": "N/A",
        "session": "2026",
        "exam": "1st Term",
        "photo": None

    }

    subjects=[]

    subject_map={

        "bangla_w":"Bangla",
        "english_w":"English",
        "math_w":"Math",
        "arabic_w":"Arabic",
        "hindi_w":"Hindi",
        "gk_w":"GK",
        "deeniyat_w":"Deeniyat"

    }

    for key,name in subject_map.items():

        obtained = int(

            student_row[key] +

            student_row[
                key.replace(
                    "_w",
                    "_o"
                )
            ]
        )

        grade,gpa = calculate_grade(
            obtained
        )

        subjects.append({

            "name":name,
            "full_marks":50,
            "obtained":obtained,
            "grade":grade,
            "gpa":gpa

        })


    total_obtained = sum(

        x["obtained"]

        for x in subjects

    )

    final_gpa = round(

        sum(
            x["gpa"]
            for x in subjects
        ) / len(subjects),

        2
    )


    result="PASS"

    for sub in subjects:

        if sub["grade"]=="F":

            result="FAIL"
            break


    context={

        "student":student,

        "subjects":subjects,

        "total_full_marks":
        len(subjects)*50,

        "total_obtained":
        total_obtained,

        "final_grade":
        str(student_row["grade"]),

        "final_gpa":
        final_gpa,

        "result":
        result,

        "position":
        int(student_row["rank"]),

        "attendance":
        "95%",

        "remarks":
        "Excellent Performance"

    }

    request.session[
        "report_data"
    ]=context

    return render(

        request,

        "report_card.html",

        context

    )


def download_all_reports(request):

    data = request.session.get("excel_data")

    if not data:
        return HttpResponse("No Excel uploaded")

    pdf_buffer = io.BytesIO()

    template = get_template("report_pdf.html")

    # প্রথম student example
    row = data[0]

    context = {
        "student": row,
        "subjects": row.get("subjects", []),
        "total_full_marks": row.get("total_full_marks", 0),
        "total_obtained": row.get("total_obtained", 0),
        "final_grade": row.get("grade", ""),
        "final_gpa": row.get("gpa", ""),
        "result": row.get("result", ""),
        "position": row.get("rank", ""),
        "attendance": row.get("attendance", ""),
        "remarks": row.get("remarks", ""),
    }

    html = template.render(context)

    pisa.CreatePDF(
        html,
        dest=pdf_buffer,
        link_callback=link_callback
    )

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf"
    )

    response[
        "Content-Disposition"
    ] = f'attachment; filename="{row["roll"]}_{row["name"]}.pdf"'

    return response



def student_report(
    request,
    roll
):

    data = request.session.get(
        "excel_data"
    )

    if not data:

        return render(
            request,
            "upload.html",
            {
                "error": "Please upload Excel first"
            }
        )

    df = pd.DataFrame(data)

    student_row = df[
        df["roll"].astype(int)
        ==
        int(roll)
    ]

    if student_row.empty:

        return render(
            request,
            "upload.html",
            {
                "error": "Student not found"
            }
        )

    student_row = student_row.iloc[0]

    return generate_report(
        request,
        student_row
    )


def calculate_grade(mark):

    if mark >= 40:
        return "A+", 5.00

    elif mark >= 35:
        return "A", 4.00

    elif mark >= 30:
        return "A-", 3.50

    elif mark >= 25:
        return "B", 3.00

    elif mark >= 20:
        return "C", 2.00

    elif mark >= 17:
        return "D", 1.00

    else:
        return "F", 0.00
    

