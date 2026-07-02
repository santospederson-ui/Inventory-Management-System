{% extends 'base.html' %}

{% block content %}

<style>
    .page-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        flex-wrap: wrap;
        gap: 15px;
    }

    .page-header h1 {
        color: #1e3c72;
        font-weight: 700;
        font-size: 2rem;
        margin: 0;
    }

    .search-box {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }

    .search-box .form-control {
        border: 2px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px 15px;
    }

    .data-table-wrapper {
        background: white;
        border-radius: 12px;
        overflow-x: auto;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }

    .data-table-wrapper table {
        margin-bottom: 0;
        min-width: 900px;
    }

    .data-table-wrapper thead {
        background: linear-gradient(135deg,#1e3c72,#2a5298);
        color: white;
    }

    .data-table-wrapper tbody tr:hover {
        background:#f5f9ff;
    }

    .data-table-wrapper tbody td {
        padding:12px 15px;
    }

    .pagination{
        background:white;
        padding:20px;
        border-radius:12px;
        margin-top:25px;
        box-shadow:0 4px 15px rgba(0,0,0,.08);
    }

    .pagination .page-link{
        color:#1e3c72;
        border:1px solid #e0e0e0;
        border-radius:6px;
        margin:0 3px;
    }

    .pagination .page-item.active .page-link{
        background:linear-gradient(135deg,#ffc107,#ff9800);
        color:white;
    }

    .empty-state{
        text-align:center;
        padding:60px 20px;
        color:#999;
    }
</style>

<!-- HEADER -->
<div class="page-header">

    <h1>
        <i class="fas fa-boxes" style="color:#ffc107;margin-right:10px;"></i>
        Other Inventory Management
    </h1>

    <!-- SAFE ADD BUTTON -->
    {% if session.get('role') == 'admin' %}
        {% if 'other_add_item' in current_app.view_functions %}
            <a href="{{ url_for('other_add_item') }}"
               class="btn"
               style="background:linear-gradient(135deg,#51CF66,#40C057);
                      color:white;
                      padding:10px 20px;
                      border-radius:8px;">
                Add New Item
            </a>
        {% else %}
            <!-- fallback safe button -->
            <a href="#"
               class="btn"
               style="background:gray;
                      color:white;
                      padding:10px 20px;
                      border-radius:8px;
                      pointer-events:none;">
                Add New Item (Not Active)
            </a>
        {% endif %}
    {% endif %}

</div>

<!-- SEARCH -->
<div class="search-box">
<form method="GET"
      action="{{ url_for('other_inventory') }}"
      class="d-flex gap-2">

    <input type="text"
           name="search"
           value="{{ search }}"
           class="form-control"
           placeholder="Search by item name, description or category...">

</form>
</div>

<!-- TABLE -->
{% if items %}

<div class="data-table-wrapper">

<table class="table">

<thead>
<tr>
<th>#</th>
<th>Item Name</th>
<th>Description</th>
<th>Category</th>
<th>Qty</th>
<th>Remark</th>
<th>Date</th>
</tr>
</thead>

<tbody>

{% for item in items %}
<tr>

<td>{{ loop.index + ((page-1)*10) }}</td>
<td><strong>{{ item.item_name }}</strong></td>
<td>{{ item.description }}</td>
<td>{{ item.category }}</td>

<td>
{% if item.qty <= 5 %}
<span style="color:red;font-weight:bold;">{{ item.qty }}</span>
{% else %}
{{ item.qty }}
{% endif %}
</td>

<td>{{ item.remark or '-' }}</td>
<td>{{ item.created_at or 'N/A' }}</td>

</tr>
{% endfor %}

</tbody>

</table>

</div>

<!-- PAGINATION -->
<nav class="pagination">
<ul class="pagination">

{% if page > 1 %}
<li class="page-item">
<a class="page-link"
   href="{{ url_for('other_inventory', page=page-1, search=search) }}">
    Prev
</a>
</li>
{% endif %}

{% for p in range(1, total_pages+1) %}
<li class="page-item {% if p == page %}active{% endif %}">
<a class="page-link"
   href="{{ url_for('other_inventory', page=p, search=search) }}">
    {{ p }}
</a>
</li>
{% endfor %}

{% if page < total_pages %}
<li class="page-item">
<a class="page-link"
   href="{{ url_for('other_inventory', page=page+1, search=search) }}">
    Next
</a>
</li>
{% endif %}

</ul>
</nav>

{% else %}

<div class="empty-state">
<i class="fas fa-box-open"></i>
<h3>No Items Found</h3>
<p>No inventory items available.</p>
</div>

{% endif %}

{% endblock %}
