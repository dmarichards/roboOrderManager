import datetime
import html

import pandas as pd
import streamlit as st


# -----------------------------------------------------------------------------
# Configuration / reference data
# -----------------------------------------------------------------------------
st.set_page_config(page_title="RoboSystems", layout="wide")

TAX_RATE = 0.13
STATUSES = ["Draft", "Printed", "Paid"]

customers = [
    {"CustomerID": "C001", "CustomerName": "Alpha Robotics Ltd", "Address": "123 Front St", "City": "Toronto", "Prov": "Ont", "Phone": "647-555-1234", "email": "contact@alpha.com"},
    {"CustomerID": "C002", "CustomerName": "Beta Automation Inc", "Address": "45 King St", "City": "Hamilton", "Prov": "Ont", "Phone": "905-555-5678", "email": "admin@betaauto.ca"},
    {"CustomerID": "C003", "CustomerName": "Gamma Robotics", "Address": "88 Main St", "City": "London", "Prov": "Ont", "Phone": "519-555-8765", "email": "info@gammarobotics.com"},
    {"CustomerID": "C004", "CustomerName": "Delta Technology", "Address": "62 Rue Notre-Dame", "City": "Montreal", "Prov": "Que", "Phone": "514-555-4321", "email": "service@delta.ca"},
    {"CustomerID": "C005", "CustomerName": "Epsilon Solutions", "Address": "10 Harbour Rd", "City": "Sorrell", "Prov": "Que", "Phone": "450-555-2222", "email": "sales@epsilon.com"},
]

products = [
    {"ProductID": "P001", "ProductName": "Warehouse Robot", "Description": "Warehouse Robot", "UnitPrice": 24995},
    {"ProductID": "P002", "ProductName": "Humanoid Robot", "Description": "Humanoid Robot", "UnitPrice": 59995},
    {"ProductID": "P003", "ProductName": "Manufacturing Robotic Arm", "Description": "Manufacturing Robotic Arm", "UnitPrice": 49500},
    {"ProductID": "P004", "ProductName": "Drone Inspector", "Description": "Drone Inspector", "UnitPrice": 29995},
    {"ProductID": "P005", "ProductName": "Autonomous Cleaner", "Description": "Autonomous Cleaner", "UnitPrice": 35995},
    {"ProductID": "P006", "ProductName": "Assembly Line Bot", "Description": "Assembly Line Bot", "UnitPrice": 38995},
    {"ProductID": "P007", "ProductName": "Lab Cart Robot", "Description": "Lab Cart Robot", "UnitPrice": 25995},
    {"ProductID": "P008", "ProductName": "Security Patrol Bot", "Description": "Security Patrol Bot", "UnitPrice": 40495},
    {"ProductID": "P009", "ProductName": "Delivery Drone", "Description": "Delivery Drone", "UnitPrice": 27995},
    {"ProductID": "P010", "ProductName": "Inventory Tracker Bot", "Description": "Inventory Tracker Bot", "UnitPrice": 31995},
]

CUSTOMER_IDS = [c["CustomerID"] for c in customers]
CUSTOMER_BY_ID = {c["CustomerID"]: c for c in customers}


# -----------------------------------------------------------------------------
# Session state
# -----------------------------------------------------------------------------
if "order_headers" not in st.session_state:
    st.session_state["order_headers"] = [
        {
            "OrderID": "O001",
            "CustomerID": "C001",
            "CustomerName": "Alpha Robotics Ltd",
            "Date": str(datetime.date.today()),
            "Status": "Draft",
            "OrderSubtotal": 24995.00,
            "Tax": 3249.35,
            "OrderTotal": 28244.35,
        }
    ]

if "order_details" not in st.session_state:
    st.session_state["order_details"] = [
        {
            "OrderID": "O001",
            "ProductID": "P001",
            "Description": "Warehouse Robot",
            "Quantity": 1,
            "UnitPrice": 24995.00,
            "LineTotal": 24995.00,
        }
    ]

st.session_state.setdefault("selected_order", "O001")
st.session_state.setdefault("selector_version", 0)
st.session_state.setdefault("add_header_version", 0)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def money(value):
    return f"${float(value):,.2f}"


def get_order_header(order_id):
    return next(
        (h for h in st.session_state["order_headers"] if h["OrderID"] == order_id),
        None,
    )


def get_order_details(order_id):
    return [d for d in st.session_state["order_details"] if d["OrderID"] == order_id]


def recalculate_order_totals(order_id):
    header = get_order_header(order_id)
    if header is None:
        return

    subtotal = round(sum(float(d["LineTotal"]) for d in get_order_details(order_id)), 2)
    tax = round(subtotal * TAX_RATE, 2)
    header["OrderSubtotal"] = subtotal
    header["Tax"] = tax
    header["OrderTotal"] = round(subtotal + tax, 2)


def normalize_date(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass

    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()

    try:
        return pd.to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return None


def clean_text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).strip()


def validate_header_values(
    order_id,
    customer_id,
    status,
    order_date,
    existing_order_ids,
    check_duplicate_order_id=True,
):
    """Validate normalized header values and return a list of user-facing errors."""
    errors = []

    if not order_id:
        errors.append("OrderID is required.")
    elif check_duplicate_order_id and order_id in existing_order_ids:
        errors.append(f"OrderID {order_id} already exists.")

    if not customer_id:
        errors.append("CustomerID is required.")
    elif customer_id not in CUSTOMER_BY_ID:
        errors.append(
            f"CustomerID {customer_id} was not found. "
            f"Valid IDs are: {', '.join(CUSTOMER_IDS)}."
        )

    if not status:
        errors.append("Status is required.")
    elif status not in STATUSES:
        errors.append(f"Status must be one of: {', '.join(STATUSES)}.")

    if order_date is None:
        errors.append("Date is required and must be in YYYY-MM-DD format.")

    return errors


def show_header_table(header=None, add_mode=False, key_prefix="header"):
    """
    Render the Order Header as a one-row table using normal Streamlit widgets.

    This intentionally does not use st.data_editor. Each editable value has its
    own widget state, so Add/Save reads the exact values currently on screen.
    """
    if add_mode:
        defaults = {
            "OrderID": "",
            "Date": "",
            "CustomerID": "",
            "CustomerName": "",
            "Status": "",
            "OrderSubtotal": 0.00,
            "Tax": 0.00,
            "OrderTotal": 0.00,
        }
    else:
        defaults = {
            "OrderID": header["OrderID"],
            "Date": header["Date"],
            "CustomerID": header["CustomerID"],
            "CustomerName": header["CustomerName"],
            "Status": header["Status"],
            "OrderSubtotal": float(header["OrderSubtotal"]),
            "Tax": float(header["Tax"]),
            "OrderTotal": float(header["OrderTotal"]),
        }

    labels = [
        "OrderID",
        "Date",
        "CustomerID",
        "Customer Name",
        "Status",
        "Subtotal",
        "Tax",
        "Total",
    ]
    widths = [1.0, 1.25, 1.05, 1.8, 1.05, 1.15, 1.0, 1.15]

    with st.container(border=True):
        header_cols = st.columns(widths, gap="small")
        for col, label in zip(header_cols, labels):
            col.markdown(f"**{label}**")

        value_cols = st.columns(widths, gap="small")

        with value_cols[0]:
            order_id = st.text_input(
                "OrderID value",
                value=defaults["OrderID"],
                key=f"{key_prefix}_order_id",
                disabled=not add_mode,
                placeholder="O002",
                label_visibility="collapsed",
            )

        with value_cols[1]:
            # A text field is deliberate here: it can start truly blank in Add
            # mode and validation can enforce YYYY-MM-DD consistently.
            date_value = st.text_input(
                "Date value",
                value=defaults["Date"],
                key=f"{key_prefix}_date",
                placeholder="YYYY-MM-DD",
                label_visibility="collapsed",
            )

        with value_cols[2]:
            customer_id_value = st.text_input(
                "CustomerID value",
                value=defaults["CustomerID"],
                key=f"{key_prefix}_customer_id",
                placeholder="C002",
                label_visibility="collapsed",
            )

        normalized_customer_id = clean_text(customer_id_value).upper()
        customer_name = CUSTOMER_BY_ID.get(normalized_customer_id, {}).get(
            "CustomerName", ""
        )

        # Keep the read-only display synchronized with the entered CustomerID.
        customer_name_key = f"{key_prefix}_customer_name_display"
        st.session_state[customer_name_key] = customer_name
        with value_cols[3]:
            st.text_input(
                "Customer Name value",
                key=customer_name_key,
                disabled=True,
                placeholder="Resolved from CustomerID",
                label_visibility="collapsed",
            )

        with value_cols[4]:
            status_options = [""] + STATUSES
            default_status = defaults["Status"] if defaults["Status"] in status_options else ""
            status_value = st.selectbox(
                "Status value",
                status_options,
                index=status_options.index(default_status),
                key=f"{key_prefix}_status",
                label_visibility="collapsed",
            )

        # Read-only financial fields. Set their widget state immediately before
        # rendering so recalculated totals always display the current values.
        financial_fields = [
            (5, "subtotal", money(defaults["OrderSubtotal"])),
            (6, "tax", money(defaults["Tax"])),
            (7, "total", money(defaults["OrderTotal"])),
        ]
        for column_index, field_name, display_value in financial_fields:
            display_key = f"{key_prefix}_{field_name}_display"
            st.session_state[display_key] = display_value
            with value_cols[column_index]:
                st.text_input(
                    f"{field_name.title()} value",
                    key=display_key,
                    disabled=True,
                    label_visibility="collapsed",
                )

    return {
        "OrderID": clean_text(order_id),
        "Date": normalize_date(date_value),
        "CustomerID": normalized_customer_id,
        "CustomerName": customer_name,
        "Status": clean_text(status_value),
    }

def render_print_header(header):
    cells = [
        ("OrderID", header["OrderID"]),
        ("Date", header["Date"]),
        ("Status", header["Status"]),
        ("CustomerID", header["CustomerID"]),
        ("Customer Name", header["CustomerName"]),
        ("Subtotal", money(header["OrderSubtotal"])),
        ("Tax", money(header["Tax"])),
        ("Total", money(header["OrderTotal"])),
    ]

    headings = "".join(f"<th>{html.escape(str(label))}</th>" for label, _ in cells)
    values = "".join(f"<td>{html.escape(str(value))}</td>" for _, value in cells)

    st.markdown(
        f"""
        <div class="print-table-wrap">
          <table class="print-table">
            <thead><tr>{headings}</tr></thead>
            <tbody><tr>{values}</tr></tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_print_details(details, header):
    body = ""
    for detail in details:
        body += f"""
        <tr>
          <td>{html.escape(str(detail['ProductID']))}</td>
          <td>{html.escape(str(detail['Description']))}</td>
          <td class="num">{html.escape(str(detail['Quantity']))}</td>
          <td class="num">{html.escape(money(detail['UnitPrice']))}</td>
          <td class="num">{html.escape(money(detail['LineTotal']))}</td>
        </tr>
        """

    for label, value, css_class in [
        ("Subtotal", header["OrderSubtotal"], ""),
        ("Tax", header["Tax"], ""),
        ("Total", header["OrderTotal"], " total-row"),
    ]:
        body += f"""
        <tr class="summary-row{css_class}">
          <td colspan="4" class="summary-label">{label}</td>
          <td class="num">{html.escape(money(value))}</td>
        </tr>
        """

    st.markdown(
        f"""
        <div class="print-table-wrap">
          <table class="print-table">
            <thead>
              <tr>
                <th>ProductID</th>
                <th>Description</th>
                <th class="num">Quantity</th>
                <th class="num">UnitPrice</th>
                <th class="num">LineTotal</th>
              </tr>
            </thead>
            <tbody>{body}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# Styling for Print Order tables
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .print-table-wrap {
        width: 100%;
        overflow-x: auto;
        margin-bottom: 1rem;
      }
      table.print-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.95rem;
      }
      table.print-table th,
      table.print-table td {
        border: 1px solid rgba(128, 128, 128, 0.35);
        padding: 0.55rem 0.65rem;
        vertical-align: top;
      }
      table.print-table th {
        font-weight: 700;
        text-align: left;
      }
      table.print-table .num {
        text-align: right;
        white-space: nowrap;
      }
      table.print-table .summary-label {
        text-align: right;
        font-weight: 600;
      }
      table.print-table .total-row td {
        font-weight: 700;
        border-top-width: 2px;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Navigation
# -----------------------------------------------------------------------------
st.sidebar.header("Order Actions")
action = st.sidebar.radio("Select Action", ["Edit", "Add", "Delete"])

st.title("RoboSystems Orders Management")

if "flash_message" in st.session_state:
    st.success(st.session_state.pop("flash_message"))

tab1, tab2, tab3 = st.tabs(["Order Header", "Order Details", "Print Order"])


# -----------------------------------------------------------------------------
# ORDER HEADER
# -----------------------------------------------------------------------------
with tab1:
    st.header("Order Header")

    order_ids = [h["OrderID"] for h in st.session_state["order_headers"]]

    if order_ids:
        if st.session_state["selected_order"] not in order_ids:
            st.session_state["selected_order"] = order_ids[0]

        selected_order = st.selectbox(
            "Select Order",
            order_ids,
            index=order_ids.index(st.session_state["selected_order"]),
            key=f"order_selector_{st.session_state['selector_version']}",
        )
        st.session_state["selected_order"] = selected_order
        current_header = get_order_header(selected_order)
    else:
        selected_order = ""
        current_header = None
        st.session_state["selected_order"] = ""
        st.info("No orders exist yet. Choose Add to create the first order.")

    st.subheader("Order Header Information")

    # ADD: same one-row header table as Edit, but blank. OrderID is editable.
    if action == "Add":
        add_values = show_header_table(
            header=None,
            add_mode=True,
            key_prefix=f"add_header_{st.session_state['add_header_version']}",
        )

        if st.button("Add Order Header", type="primary", key="add_order_header_button"):
            order_id = add_values["OrderID"]
            customer_id = add_values["CustomerID"]
            status = add_values["Status"]
            order_date = add_values["Date"]

            errors = validate_header_values(
                order_id=order_id,
                customer_id=customer_id,
                status=status,
                order_date=order_date,
                existing_order_ids=order_ids,
                check_duplicate_order_id=True,
            )

            if errors:
                for error in errors:
                    st.error(error)
            else:
                customer_name = CUSTOMER_BY_ID[customer_id]["CustomerName"]
                st.session_state["order_headers"].append(
                    {
                        "OrderID": order_id,
                        "CustomerID": customer_id,
                        "CustomerName": customer_name,
                        "Date": order_date,
                        "Status": status,
                        "OrderSubtotal": 0.00,
                        "Tax": 0.00,
                        "OrderTotal": 0.00,
                    }
                )

                # Select the new order and force a fresh set of Add widget keys,
                # which clears every Add field after a successful save.
                st.session_state["selected_order"] = order_id
                st.session_state["selector_version"] += 1
                st.session_state["add_header_version"] += 1
                st.session_state["flash_message"] = (
                    f"Added new order {order_id} for {customer_name}. "
                    "The Add table has been cleared."
                )
                st.rerun()

    # EDIT: Date, CustomerID and Status editable; all other fields read-only.
    elif action == "Edit":
        if current_header is not None:
            edit_values = show_header_table(
                header=current_header,
                add_mode=False,
                key_prefix=f"edit_header_{selected_order}",
            )

            if st.button("Save Changes", type="primary", key=f"save_header_{selected_order}"):
                customer_id = edit_values["CustomerID"]
                status = edit_values["Status"]
                order_date = edit_values["Date"]

                errors = validate_header_values(
                    order_id=selected_order,
                    customer_id=customer_id,
                    status=status,
                    order_date=order_date,
                    existing_order_ids=order_ids,
                    check_duplicate_order_id=False,
                )

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    customer = CUSTOMER_BY_ID[customer_id]
                    current_header["Date"] = order_date
                    current_header["CustomerID"] = customer_id
                    current_header["CustomerName"] = customer["CustomerName"]
                    current_header["Status"] = status
                    st.success(
                        f"Order header updated. Customer: {customer['CustomerName']}."
                    )

    elif action == "Delete":
        if current_header is not None:
            # Keep the same header table visible in Delete mode, but with no
            # editable fields. Delete is still an explicit separate action.
            show_header_table(
                header=current_header,
                add_mode=False,
                key_prefix=f"delete_header_{selected_order}",
            )

            if st.button("Delete Order", type="primary"):
                st.session_state["order_headers"] = [
                    h for h in st.session_state["order_headers"]
                    if h["OrderID"] != selected_order
                ]
                st.session_state["order_details"] = [
                    d for d in st.session_state["order_details"]
                    if d["OrderID"] != selected_order
                ]

                remaining = [h["OrderID"] for h in st.session_state["order_headers"]]
                st.session_state["selected_order"] = remaining[0] if remaining else ""
                st.session_state["selector_version"] += 1
                st.session_state["flash_message"] = f"Deleted order {selected_order}."
                st.rerun()


# -----------------------------------------------------------------------------
# ORDER DETAILS
# -----------------------------------------------------------------------------
with tab2:
    st.header("Order Details")

    selected_order = st.session_state["selected_order"]
    current_header = get_order_header(selected_order)

    if current_header is None:
        st.info("Select or add an order before working with order details.")
    else:
        st.caption(f"Current Order: {selected_order}")
        order_details = get_order_details(selected_order)

        if order_details:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "ProductID": d["ProductID"],
                            "Description": d["Description"],
                            "Quantity": d["Quantity"],
                            "UnitPrice": money(d["UnitPrice"]),
                            "LineTotal": money(d["LineTotal"]),
                        }
                        for d in order_details
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No order details for this order.")

        if action == "Add":
            st.subheader("Add Order Detail")
            with st.form("add_detail"):
                product_name = st.selectbox("Product", [p["ProductName"] for p in products])
                product = next(p for p in products if p["ProductName"] == product_name)

                # Negative quantities are allowed because there is no min_value.
                qty = st.number_input("Quantity", value=1, step=1)
                submitted = st.form_submit_button("Add Order Detail")

            if submitted:
                st.session_state["order_details"].append(
                    {
                        "OrderID": selected_order,
                        "ProductID": product["ProductID"],
                        "Description": product["Description"],
                        "Quantity": qty,
                        "UnitPrice": float(product["UnitPrice"]),
                        "LineTotal": float(qty) * float(product["UnitPrice"]),
                    }
                )
                recalculate_order_totals(selected_order)
                st.success("Added order detail.")

        elif action == "Edit":
            st.subheader("Edit Order Detail")
            if order_details:
                detail_idx = st.selectbox(
                    "Select item to edit",
                    range(len(order_details)),
                    format_func=lambda i: f"{order_details[i]['ProductID']} - {order_details[i]['Description']}",
                )
                detail = order_details[detail_idx]

                with st.form("edit_detail"):
                    new_desc = st.text_input("Description", value=detail["Description"])

                    # Negative quantities are allowed here too.
                    new_qty = st.number_input(
                        "Quantity",
                        value=int(detail["Quantity"]),
                        step=1,
                    )
                    new_unit_price = st.number_input(
                        "UnitPrice",
                        value=float(detail["UnitPrice"]),
                        min_value=0.0,
                        step=100.0,
                        format="%.2f",
                    )
                    submitted = st.form_submit_button("Save Detail Changes")

                if submitted:
                    detail["Description"] = new_desc
                    detail["Quantity"] = new_qty
                    detail["UnitPrice"] = float(new_unit_price)
                    detail["LineTotal"] = float(new_qty) * float(new_unit_price)
                    recalculate_order_totals(selected_order)
                    st.success("Updated order detail.")

        elif action == "Delete":
            st.subheader("Delete Order Detail")
            if order_details:
                detail_idx = st.selectbox(
                    "Select item to delete",
                    range(len(order_details)),
                    format_func=lambda i: f"{order_details[i]['ProductID']} - {order_details[i]['Description']}",
                    key="delete_detail_selector",
                )
                detail = order_details[detail_idx]

                if st.button("Delete Detail"):
                    st.session_state["order_details"].remove(detail)
                    recalculate_order_totals(selected_order)
                    st.success("Deleted order detail.")


# -----------------------------------------------------------------------------
# PRINT ORDER
# -----------------------------------------------------------------------------
with tab3:
    st.header("Printable Order Summary")

    selected_order = st.session_state["selected_order"]
    current_header = get_order_header(selected_order)

    if current_header is None:
        st.info("No order selected.")
    else:
        st.subheader("Order Header")
        render_print_header(current_header)

        st.subheader("Order Details")
        render_print_details(get_order_details(selected_order), current_header)