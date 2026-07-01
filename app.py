from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "inventory_secret_key"


import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="da8y4zqz5",
    api_key="551545451643298",
    api_secret="CtN8D84Db81NFkhUwGUm8W2cvEU"
)


# =========================
# DATABASE CONNECTION
# =========================
import os
import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        port=int(os.environ.get("MYSQLPORT", 3306))
    )

# =========================
# HOME
# =========================
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Admin login (hardcoded)
        if role == "admin":
            if username == "admin" and password == "admin123":
                session['user'] = username
                session['role'] = "admin"
                flash("Admin Login Successful", "success")
                return redirect(url_for('dashboard'))

        # User login (DB)
        if role == "user":

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT * FROM users WHERE username=%s",
                (username,)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user and check_password_hash(user['password'], password):
                session['user'] = username
                session['role'] = "user"
                flash("Login Successful", "success")
                return redirect(url_for('dashboard'))

        flash("Invalid Credentials", "danger")

    return render_template('login.html')


# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():

    if 'user' not in session:
        return redirect(url_for('login'))

    page = request.args.get('page', 1, type=int)
    per_page = 5
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # =========================
    # LOW STOCK (PAGINATED)
    # =========================
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM inventory_table
        WHERE qty <= 5
    """)
    total = cursor.fetchone()['total']

    cursor.execute("""
        SELECT *
        FROM inventory_table
        WHERE qty <= 5
        ORDER BY qty ASC
        LIMIT %s OFFSET %s
    """, (per_page, offset))

    low_stock = cursor.fetchall()

    total_pages = (total + per_page - 1) // per_page


    # =========================
    # RECENT WITHDRAWALS (NO PAGINATION)
    # =========================
    cursor.execute("""
        SELECT *
        FROM withdrawals_table
        ORDER BY action_date DESC
        LIMIT 5
    """)
    recent_withdrawals = cursor.fetchall()


    # =========================
    # RECENT RETURNS (NO PAGINATION)
    # =========================
    cursor.execute("""
        SELECT *
        FROM return_tab
        ORDER BY action_date DESC
        LIMIT 5
    """)
    recent_returns = cursor.fetchall()


    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        username=session['user'],
        role=session['role'],
        low_stock=low_stock,
        recent_withdrawals=recent_withdrawals,
        recent_returns=recent_returns,
        page=page,
        total_pages=total_pages
    )


# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():

    session.clear()
    flash("Logged Out Successfully", "info")
    return redirect(url_for('login'))


# =========================
# REGISTER USER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['fullname']
        username = request.form['username']
        password = request.form['password']

        # Hash the password before storing
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (fullname, username, password)
            VALUES (%s, %s, %s)
        """, (fullname, username, hashed_password))

        conn.commit()

        cursor.close()
        conn.close()

        flash("User Registered Successfully", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


# =========================
# INVENTORY LIST ROUTE
# =========================
@app.route('/inventory')
def inventory():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM inventory_table
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR brand LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM inventory_table
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR brand LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute(
            "SELECT COUNT(*) AS total FROM inventory_table"
        )
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM inventory_table
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'inventory.html',
        items=items,
        page=page,
        total_pages=total_pages,
        search=search
    )

# =========================
# ADD ITEM (ADMIN)
# =========================
@app.route('/add_item', methods=['GET', 'POST'])
def add_item():

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    if request.method == 'POST':

        item_code = request.form['item_code']
        description = request.form['description']
        brand = request.form['brand']
        qty = request.form['qty']
        remark = request.form['remark']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO inventory_table
            (item_code, description, brand, qty, remark)
            VALUES (%s,%s,%s,%s,%s)
        """, (item_code, description, brand, qty, remark))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Item Added Successfully", "success")
        return redirect(url_for('inventory'))

    return render_template('add_item.html')


# =========================
# EDIT ITEM (ADMIN)
# =========================
@app.route('/edit_item/<int:id>', methods=['GET', 'POST'])
def edit_item(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        item_code = request.form['item_code']
        description = request.form['description']
        brand = request.form['brand']
        qty = request.form['qty']
        remark = request.form['remark']

        cursor.execute("""
            UPDATE inventory_table
            SET item_code=%s,
                description=%s,
                brand=%s,
                qty=%s,
                remark=%s
            WHERE id=%s
        """, (item_code, description, brand, qty, remark, id))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Item Updated", "success")
        return redirect(url_for('inventory'))

    cursor.execute("SELECT * FROM inventory_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('edit_item.html', item=item)


# =========================
# DELETE ITEM (ADMIN)
# =========================
@app.route('/delete_item/<int:id>')
def delete_item(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM inventory_table WHERE id=%s", (id,))

    conn.commit()

    cursor.close()
    conn.close()

    flash("Item Deleted", "warning")
    return redirect(url_for('inventory'))



# =========================
# AUDIT ROUTE
# =========================

@app.route('/audit')
def audit():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # SEARCH ACTIVE
    if search:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM (

                SELECT item_code, description, project,
                       withdrawn_by AS user
                FROM withdrawals_table

                UNION ALL

                SELECT item_code, description, project,
                       returned_by AS user
                FROM return_tab

                UNION ALL

                SELECT item_code, description,
                       remark AS project,
                       added_by AS user
                FROM stock_addition

            ) AS audit_data

            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR user LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM (

                SELECT
                    item_code,
                    description,
                    qty,
                    project,
                    withdrawn_by AS user,
                    action_date,
                    'WITHDRAWAL' AS action
                FROM withdrawals_table

                UNION ALL

                SELECT
                    item_code,
                    description,
                    qty,
                    project,
                    returned_by AS user,
                    action_date,
                    'RETURN' AS action
                FROM return_tab

                UNION ALL

                SELECT
                    item_code,
                    description,
                    qty,
                    remark AS project,
                    added_by AS user,
                    action_date,
                    'STOCK ADD' AS action
                FROM stock_addition

            ) AS audit_data

            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR user LIKE %s

            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM (
                SELECT action_date FROM withdrawals_table
                UNION ALL
                SELECT action_date FROM return_tab
                UNION ALL
                SELECT action_date FROM stock_addition
            ) AS audit_data
        """)

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM (

                SELECT
                    item_code,
                    description,
                    qty,
                    project,
                    withdrawn_by AS user,
                    action_date,
                    'WITHDRAWAL' AS action
                FROM withdrawals_table

                UNION ALL

                SELECT
                    item_code,
                    description,
                    qty,
                    project,
                    returned_by AS user,
                    action_date,
                    'RETURN' AS action
                FROM return_tab

                UNION ALL

                SELECT
                    item_code,
                    description,
                    qty,
                    remark AS project,
                    added_by AS user,
                    action_date,
                    'STOCK ADD' AS action
                FROM stock_addition

            ) AS audit_data

            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    logs = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "audit.html",
        logs=logs,
        page=page,
        total_pages=total_pages,
        search=search
    )


# =========================
# WITHDRAWER ROUTE
# =========================


@app.route('/withdraw/<int:id>', methods=['GET', 'POST'])
def withdraw(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM inventory_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    if request.method == 'POST':

        qty = int(request.form['qty'])
        project = request.form['project']

        if qty > item['qty']:
            flash("Not enough stock", "danger")
            return redirect(url_for('inventory'))

        # reduce stock
        cursor.execute("""
            UPDATE inventory_table
            SET qty = qty - %s
            WHERE id = %s
        """, (qty, id))

        # log withdrawal
        cursor.execute("""
            INSERT INTO withdrawals_table
            (item_id, item_code, description, qty, project, withdrawn_by)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            id,
            item['item_code'],
            item['description'],
            qty,
            project,
            session['user']
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Item Withdrawn Successfully", "success")
        return redirect(url_for('inventory'))

    cursor.close()
    conn.close()

    return render_template('withdraw.html', item=item)



# =========================
# RETURN ROUTE
# =========================


@app.route('/return_item/<int:id>', methods=['GET', 'POST'])
def return_item(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM inventory_table WHERE id=%s",
        (id,)
    )
    item = cursor.fetchone()

    if request.method == 'POST':

        qty = int(request.form['qty'])
        project = request.form['project']
        remark = request.form['remark']

        # Increase stock
        cursor.execute("""
            UPDATE inventory_table
            SET qty = qty + %s
            WHERE id = %s
        """, (qty, id))

        # Save return record
        cursor.execute("""
            INSERT INTO return_tab
            (
                item_id,
                item_code,
                description,
                qty,
                returned_by,
                project,
                remark,
                action_date
            )
            VALUES
            (%s,%s,%s,%s,%s,%s,%s,NOW())
        """, (
            id,
            item['item_code'],
            item['description'],
            qty,
            session['user'],
            project,
            remark
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Item Returned Successfully", "success")
        return redirect(url_for('inventory'))

    cursor.close()
    conn.close()

    return render_template('return.html', item=item)



# =========================
# ADD STOCK ROUTE
# =========================


@app.route('/add_stock/<int:id>', methods=['GET', 'POST'])
def add_stock(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM inventory_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    if request.method == 'POST':
        qty = int(request.form['qty'])
        remark = request.form['remark']  # ✅ ADD THIS

        # increase stock
        cursor.execute("""
            UPDATE inventory_table
            SET qty = qty + %s
            WHERE id = %s
        """, (qty, id))

        # log into stock_addition table
        cursor.execute("""
            INSERT INTO stock_addition
            (item_id, item_code, description, qty, added_by, remark)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            id,
            item['item_code'],
            item['description'],
            qty,
            session['user'],
            remark
        ))
        conn.commit()

        cursor.close()
        conn.close()

        flash("Stock Added Successfully", "success")
        return redirect(url_for('inventory'))

    cursor.close()
    conn.close()

    return render_template('add_stock.html', item=item)



# =========================
# DISPLAY WITHDRAWAL TABLE
# =========================



@app.route('/withdrawals')
def withdrawals():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        # Count filtered records
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM withdrawals_table
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR withdrawn_by LIKE %s

             
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        # Get filtered records
        cursor.execute("""
            SELECT *
            FROM withdrawals_table
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR withdrawn_by LIKE %s
           ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM withdrawals_table
        """)

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM withdrawals_table
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'withdrawals.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )

# =========================
# DISPLAY RETURN TABLE
# =========================



@app.route('/returns')
def returns():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        # Count matching records
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM return_tab
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        # Get matching records
        cursor.execute("""
            SELECT *
            FROM return_tab
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        # Total rows
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM return_tab
        """)

        total = cursor.fetchone()['total']

        # Current page rows
        cursor.execute("""
            SELECT *
            FROM return_tab
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'returns.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )



# =========================
# DISPLAY ADD STOCK TABLE
# =========================

@app.route('/stock_additions')
def stock_additions():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # SEARCH ACTIVE
    if search:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM stock_addition
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR added_by LIKE %s
               OR remark LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM stock_addition
            WHERE item_code LIKE %s
               OR description LIKE %s
               OR added_by LIKE %s
               OR remark LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    # NO SEARCH
    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM stock_addition
        """)
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM stock_addition
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'stock_additions.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )


# =========================
# TILE INVENTORY LIST ROUTE
# =========================
@app.route('/tile_inventory')
def tile_inventory():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_inventory_table
            WHERE size LIKE %s
               OR description LIKE %s
               OR type LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM tile_inventory_table
            WHERE size LIKE %s
               OR description LIKE %s
               OR type LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_inventory_table
        """)
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM tile_inventory_table
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (
            per_page,
            offset
        ))

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'tile_inventory.html',
        items=items,
        page=page,
        total_pages=total_pages,
        search=search
    )



# =========================
# EDIT TILE ROUTE(ADMIN)
# =========================
@app.route('/tile_edit_item/<int:id>', methods=['GET', 'POST'])
def tile_edit_item(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        size = request.form['size']
        description = request.form['description']
        type = request.form['type']
        qty = float(request.form['qty'])
        remark = request.form['remark']

        cursor.execute("""
            UPDATE tile_inventory_table
            SET size=%s,
                description=%s,
                type=%s,
                qty=%s,
                remark=%s
            WHERE id=%s
        """, (size, description, type, qty, remark, id))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Tile Updated", "success")
        return redirect(url_for('tile_inventory'))

    cursor.execute(
        "SELECT * FROM tile_inventory_table WHERE id=%s",
        (id,)
    )
    item = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'tile_edit_item.html',
        item=item
    )


# =========================
# DELETE TILE ROUTE (ADMIN)
# =========================
@app.route('/delete_tile/<int:id>')
def delete_tile(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM tile_inventory_table WHERE id=%s",
        (id,)
    )

    conn.commit()

    cursor.close()
    conn.close()

    flash("Tile Deleted", "warning")
    return redirect(url_for('tile_inventory'))


# =========================
# TILE WITHDRAW ROUTE
# =========================

@app.route('/tile_withdraw/<int:id>', methods=['GET', 'POST'])
def tile_withdraw(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tile_inventory_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    if request.method == 'POST':

        qty = float(request.form['qty'])
        project = request.form['project']

        if qty > item['qty']:
            flash("Not enough stock", "danger")
            return redirect(url_for('tile_inventory'))

        # reduce stock
        cursor.execute("""
            UPDATE tile_inventory_table
            SET qty = qty - %s
            WHERE id = %s
        """, (qty, id))

        # log withdrawal
        cursor.execute("""
            INSERT INTO tile_withdrawals_table
            (item_id, size, description, qty, project, withdrawn_by)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            id,
            item['size'],
            item['description'],
            qty,
            project,
            session['user']
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Tile Withdrawn Successfully", "success")
        return redirect(url_for('tile_inventory'))

    cursor.close()
    conn.close()

    return render_template('tile_withdraw.html', item=item)



# =========================
# TILE RETURN ROUTE
# =========================

@app.route('/tile_return_item/<int:id>', methods=['GET', 'POST'])
def tile_return_item(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get tile item
    cursor.execute(
        "SELECT * FROM tile_inventory_table WHERE id=%s",
        (id,)
    )
    item = cursor.fetchone()

    if not item:
        cursor.close()
        conn.close()
        flash("Tile not found", "danger")
        return redirect(url_for('tile_inventory'))

    if request.method == 'POST':

        qty = float(request.form['qty'])
        project = request.form['project']
        remark = request.form['remark']

        # Add quantity back to inventory
        cursor.execute("""
            UPDATE tile_inventory_table
            SET qty = qty + %s
            WHERE id = %s
        """, (qty, id))

        # Log return
        cursor.execute("""
            INSERT INTO tile_return_tab
            (
                item_id,
                size,
                description,
                qty,
                project,
                returned_by,
                remark
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            id,
            item['size'],
            item['description'],
            qty,
            project,
            session['user'],
            remark
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Tile Returned Successfully", "success")
        return redirect(url_for('tile_inventory'))

    cursor.close()
    conn.close()

    return render_template(
        'tile_return_item.html',
        item=item
    )



# =========================
# ADD TILE STOCK ROUTE
# =========================



@app.route('/tile_add_stock/<int:id>', methods=['GET', 'POST'])
def tile_add_stock(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM tile_inventory_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    if request.method == 'POST':
        qty = float(request.form['qty'])
        remark = request.form['remark']

        # increase stock
        cursor.execute("""
            UPDATE tile_inventory_table
            SET qty = qty + %s
            WHERE id = %s
        """, (qty, id))

        # log stock addition
        cursor.execute("""
            INSERT INTO tile_stock_addition
            (item_id, size, description, qty, added_by, remark)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            id,
            item['size'],
            item['description'],
            qty,
            session['user'],
            remark
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Tile Stock Added Successfully", "success")
        return redirect(url_for('tile_inventory'))

    cursor.close()
    conn.close()

    return render_template('tile_add_stock.html', item=item)





# =========================
# ADD TILE ITEM (ADMIN)
# =========================

@app.route('/tile_add_item', methods=['GET', 'POST'])
def tile_add_item():

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('tile_inventory'))

    if request.method == 'POST':

        size = request.form['size']
        description = request.form['description']
        tile_type = request.form['type']
        qty = float(request.form['qty'])
        remark = request.form['remark']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tile_inventory_table
            (size, description, type, qty, remark)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            size,
            description,
            tile_type,
            qty,
            remark
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Tile Added Successfully", "success")
        return redirect(url_for('tile_inventory'))

    return render_template('tile_add_item.html')



# =========================
# TILE WITHDRAWAL HISTORY
# =========================

@app.route('/tile_withdrawals')
def tile_withdrawals():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        # Count filtered records
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_withdrawals_table
            WHERE size LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR withdrawn_by LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        # Get filtered records
        cursor.execute("""
            SELECT *
            FROM tile_withdrawals_table
            WHERE size LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR withdrawn_by LIKE %s
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_withdrawals_table
        """)

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM tile_withdrawals_table
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (
            per_page,
            offset
        ))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'tile_withdrawals.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )



# =========================
# DISPLAY TILE RETURN TABLE
# =========================

@app.route('/tile_returns')
def tile_returns():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        # Count matching records
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_return_tab
            WHERE size LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        # Get matching records
        cursor.execute("""
            SELECT *
            FROM tile_return_tab
            WHERE size LIKE %s
               OR description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        # Total rows
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM tile_return_tab
        """)

        total = cursor.fetchone()['total']

        # Current page rows
        cursor.execute("""
            SELECT *
            FROM tile_return_tab
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'tile_returns.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )



# =========================
# UPLOAD IMAGE ROUTE
# =========================
# =========================
# PDF RECORD ROUTE
# =========================

from flask import request, redirect, url_for, flash, render_template, session

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():

    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':

        description = request.form.get('description')
        filename = request.form.get('filename')
        remark = request.form.get('remark')

        if not filename:
            flash("Please enter a PDF filename", "danger")
            return redirect(url_for('upload_image'))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO upload_table
            (full_description, filename, remark)
            VALUES (%s, %s, %s)
        """, (
            description,
            filename,
            remark
        ))

        conn.commit()
        cursor.close()
        conn.close()

        
        return redirect(url_for('upload_list'))
        flash("Record saved successfully", "success")
    return render_template('upload_image.html')
# =========================
# UPLOAD LIST ROUTE
# =========================

@app.route('/upload_list')
def upload_list():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = "FROM upload_table"
    where_clause = ""
    params = []

    if search:
        where_clause = """
            WHERE full_description LIKE %s
               OR remark LIKE %s
        """
        params.extend([f"%{search}%", f"%{search}%"])

    # COUNT
    cursor.execute(f"SELECT COUNT(*) AS total {base_query} {where_clause}", params)
    total = cursor.fetchone()['total']

    # DATA
    cursor.execute(f"""
        SELECT *
        {base_query}
        {where_clause}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        "upload_list.html",
        data=data,
        search=search,
        page=page,
        total_pages=total_pages
    )




#==========================
# MARBLE LIST ROUTE
# =========================

@app.route('/marble')
def marble():

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM marble_table
            WHERE description LIKE %s
        """, (f"%{search}%",))
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM marble_table
            WHERE description LIKE %s
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (f"%{search}%", per_page, offset))

    else:

        cursor.execute("SELECT COUNT(*) AS total FROM marble_table")
        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT *
            FROM marble_table
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    items = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'marble.html',
        marbles=items,   # or items depending on your HTML
        page=page,
        total_pages=total_pages,
        search=search
    )


# =========================
# ADD MARBLE ROUTE APP
# =========================

@app.route('/add_marble', methods=['GET', 'POST'])
def add_marble():

    if request.method == 'POST':

        description = request.form.get('description')
        qty = request.form.get('qty')
        project = request.form.get('project')
        remark = request.form.get('remark')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO marble_table
            (description, qty, project, remark)
            VALUES (%s, %s, %s, %s)
        """, (
            description,
            qty,
            project,
            remark
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Marble item added successfully', 'success')
        return redirect(url_for('marble'))

    return render_template('add_marble.html')



# =========================
# EDITH MARBLE
# =========================



@app.route('/edit_marble/<int:id>', methods=['GET', 'POST'])
def edit_marble(id):

    if 'user' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':

        description = request.form.get('description')
        qty = request.form.get('qty')
        project = request.form.get('project')
        remark = request.form.get('remark')

        cursor.execute("""
            UPDATE marble_table
            SET
                description = %s,
                qty = %s,
                project = %s,
                remark = %s
            WHERE id = %s
        """, (
            description,
            qty,
            project,
            remark,
            id
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash('Marble item updated successfully.', 'success')
        return redirect(url_for('marble'))

    cursor.execute("""
        SELECT id, description, qty, project, remark
        FROM marble_table
        WHERE id = %s
    """, (id,))

    item = cursor.fetchone()

    cursor.close()
    conn.close()

    if not item:
        flash('Marble item not found.', 'danger')
        return redirect(url_for('marble'))

    return render_template('edit_marble.html', item=item)

# =========================
# MARBLE WITHDRAW ROUTE
# =========================


@app.route('/withdraw_marble/<int:id>', methods=['GET', 'POST'])
def withdraw_marble(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('marble'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get item
    cursor.execute("SELECT * FROM marble_table WHERE id=%s", (id,))
    item = cursor.fetchone()

    if not item:
        cursor.close()
        conn.close()
        flash("Item not found", "danger")
        return redirect(url_for('marble'))

    if request.method == 'POST':

        # SAFE INPUT HANDLING (prevents 400 error)
        qty_raw = request.form.get('qty')
        project = request.form.get('project', '').strip()
        remark = request.form.get('remark', '').strip()

        # Validate qty
        try:
            qty = float(qty_raw)
        except:
            flash("Invalid quantity", "danger")
            return redirect(url_for('withdraw_marble', id=id))

        if qty <= 0:
            flash("Quantity must be greater than 0", "danger")
            return redirect(url_for('withdraw_marble', id=id))

        if not project:
            flash("Project is required", "danger")
            return redirect(url_for('withdraw_marble', id=id))

        # Stock check
        if qty > item['qty']:
            flash("Not enough stock", "danger")
            return redirect(url_for('withdraw_marble', id=id))

        # Reduce stock
        cursor.execute("""
            UPDATE marble_table
            SET qty = qty - %s
            WHERE id = %s
        """, (qty, id))

        # Log withdrawal
        cursor.execute("""
            INSERT INTO marble_withdrawals_table
            (marble_id, description, qty, project, withdrawn_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            id,
            item['description'],
            qty,
            project,
            session['user']
        ))

        conn.commit()

        cursor.close()
        conn.close()

        flash("Marble Withdrawn Successfully", "success")
        return redirect(url_for('marble'))

    cursor.close()
    conn.close()

    return render_template('withdraw_marble.html', item=item)


# =========================
# RETURN MARBLE ROUTE
# =========================


@app.route('/return_marble/<int:id>', methods=['GET', 'POST'])
def return_marble(id):

    try:
        if session.get('role') != 'admin':
            flash("Access Denied", "danger")
            return redirect(url_for('marble'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM marble_table WHERE id=%s", (id,))
        item = cursor.fetchone()

        if not item:
            flash("Marble item not found", "danger")
            return redirect(url_for('marble'))

        if request.method == 'POST':

            print("FORM DATA:", request.form)  # 🔥 DEBUG LINE

            qty = request.form.get('qty')
            project = request.form.get('project')
            remark = request.form.get('remark')

            # safety check
            if not qty or not project:
                flash("Qty and Project are required", "danger")
                return redirect(url_for('return_marble', id=id))

            qty = float(qty)

            cursor.execute("""
                UPDATE marble_table
                SET qty = qty + %s
                WHERE id = %s
            """, (qty, id))

            cursor.execute("""
                INSERT INTO marble_return_table
                (marble_id, description, qty, returned_by, project, remark, action_date)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                id,
                item['description'],
                qty,
                session.get('user'),
                project,
                remark
            ))

            conn.commit()

            flash("Marble Returned Successfully", "success")
            return redirect(url_for('marble'))

        return render_template('return_marble.html', item=item)

    except Exception as e:
        print("🔥 ERROR OCCURRED:", str(e))  # IMPORTANT
        flash("Server error occurred. Check terminal.", "danger")

    finally:
        try:
            cursor.close()
            conn.close()
        except:
            pass

# =========================
# DELETE MARBLE ROUTE
# =========================


@app.route('/delete_marble/<int:id>')
def delete_marble(id):

    if session.get('role') != 'admin':
        flash("Access Denied", "danger")
        return redirect(url_for('marble'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM marble_table WHERE id=%s", (id,))
        conn.commit()

        flash("Marble item deleted successfully", "success")

    except Exception as e:
        print("DELETE ERROR:", e)
        flash("Error deleting item", "danger")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('marble'))


from flask import request, render_template
import math



# =========================
# MARBLE WITHDRAWALS ROUTE
# =========================



# =========================
# MARBLE WITHDRAWAL HISTORY
# =========================

@app.route('/marble_withdrawals')
def marble_withdrawals():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if search:

        # Count filtered records
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM marble_withdrawals_table
            WHERE description LIKE %s
               OR project LIKE %s
               OR CAST(id AS CHAR) LIKE %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        total = cursor.fetchone()['total']

        # Get filtered records
        cursor.execute("""
            SELECT
                id,
                description,
                qty,
                project,
                withdrawn_at
            FROM marble_withdrawals_table
            WHERE description LIKE %s
               OR project LIKE %s
               OR CAST(id AS CHAR) LIKE %s
            ORDER BY withdrawn_at DESC
            LIMIT %s OFFSET %s
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%",
            per_page,
            offset
        ))

    else:

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM marble_withdrawals_table
        """)

        total = cursor.fetchone()['total']

        cursor.execute("""
            SELECT
                id,
                description,
                qty,
                project,
                withdrawn_at
            FROM marble_withdrawals_table
            ORDER BY withdrawn_at DESC
            LIMIT %s OFFSET %s
        """, (
            per_page,
            offset
        ))

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'marble_withdrawals.html',
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )





# =========================
# MARBLE RETURN HISTORY
# =========================


# =========================
# MARBLE RETURN HISTORY (FIXED)
# =========================

# =========================
# MARBLE RETURN HISTORY
# =========================

@app.route('/marble_return_item')
def marble_return_item():

    if 'user' not in session:
        return redirect(url_for('login'))

    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)

    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()

    like = f"%{search}%"

    # -------------------------
    # COUNT QUERY
    # -------------------------
    if search:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM marble_returns_table
            WHERE description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
        """, (like, like, like, like))
    else:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM marble_returns_table
        """)

    total_records = cursor.fetchone()[0]

    # -------------------------
    # DATA QUERY
    # -------------------------
    if search:
        cursor.execute("""
            SELECT 
                action_date,
                description,
                qty,
                returned_by,
                project,
                remark
            FROM marble_returns_table
            WHERE description LIKE %s
               OR project LIKE %s
               OR returned_by LIKE %s
               OR remark LIKE %s
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (like, like, like, like, per_page, offset))
    else:
        cursor.execute("""
            SELECT 
                action_date,
                description,
                qty,
                returned_by,
                project,
                remark
            FROM marble_returns_table
            ORDER BY action_date DESC
            LIMIT %s OFFSET %s
        """, (per_page, offset))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # -------------------------
    # FORMAT FOR TEMPLATE
    # -------------------------
    data = [
        {
            "action_date": r[0],
            "description": r[1],
            "qty": r[2],
            "returned_by": r[3],
            "project": r[4],
            "remark": r[5],
        }
        for r in rows
    ]

    total_pages = max(1, (total_records + per_page - 1) // per_page)

    return render_template(
        "marble_return_item.html",
        data=data,
        page=page,
        total_pages=total_pages,
        search=search
    )



# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    app.run(debug=True)
