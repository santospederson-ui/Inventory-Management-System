import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':

        description = request.form.get('description')
        remark = request.form.get('remark')
        file = request.files.get('image')

        filename = None
        filepath = None
        filetype = None

        # Handle file upload
        if file and file.filename != "":

            filename = secure_filename(file.filename)

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            file.save(filepath)

            filetype = file.content_type  # image/jpeg, application/pdf etc.

        # IMPORTANT: insert ALL columns properly
        cursor.execute("""
            INSERT INTO upload_table
            (full_description, filename, filepath, filetype, remark)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            description,
            filename,
            filepath,
            filetype,
            remark
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('upload_image'))

    cursor.close()
    conn.close()

    return render_template("upload_image.html")
