import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- File loading ----------
@st.cache_data(show_spinner=False)
def load_uploaded_file(filename, file_bytes):
    file_name = str(filename or "uploaded_file")
    ext = Path(file_name).suffix.lower()
    if ext == ".csv":
        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
            try:
                return {"CSV Data": pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, sep=None, engine="python")}
            except Exception as exc:
                last_error = exc
        raise ValueError(f"Could not read CSV: {last_error}")
    if ext in (".xlsx", ".xls"):
        workbook = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
        if isinstance(workbook, dict):
            return workbook
        return {"Sheet1": workbook}
    raise ValueError("Please upload .xlsx, .xls, or .csv files.")


def normalize_dataset_mapping(sheets):
    if sheets is None:
        return {"Data": pd.DataFrame()}
    if isinstance(sheets, pd.DataFrame):
        return {"Data": sheets}
    if isinstance(sheets, dict):
        return {str(name): frame for name, frame in sheets.items() if isinstance(frame, pd.DataFrame)}
    if isinstance(sheets, (list, tuple)):
        return {"Data": pd.DataFrame(sheets)}
    return {"Data": pd.DataFrame(sheets)}


def clean_frame(frame):
    df = frame.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")
    for col in df.columns:
        if pd.api.types.is_object_dtype(df[col]):
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    return df.reset_index(drop=True)


def find_column(columns, keywords):
    for col in columns:
        name = str(col).lower().replace("_", " ")
        if any(word in name for word in keywords):
            return col
    return None


def money(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if pd.isna(number):
        return "—"
    return f"{number:,.2f}"


def main():
    st.set_page_config(
        page_title="Data Analysis Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown("""
    <style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    [data-testid="stSidebar"] {background: #f2f5fa;}
    [data-testid="stMetric"] {
        background: #f4f8ff; border: 1px solid #e0e8f5;
        padding: 15px 16px; border-radius: 14px;
    }
    [data-testid="stMetricLabel"] {font-weight: 700;}
    h1 {color: #14264b;}
    .section-title {font-size: 1.18rem; font-weight: 750; color: #14264b; margin: 0.3rem 0 0.7rem 0;}
    .small-note {color: #68758a; font-size: 0.88rem;}
    </style>
    """, unsafe_allow_html=True)

    # ---------- Sidebar ----------
    st.sidebar.markdown("# 📊 Data Analysis")
    st.sidebar.caption("Excel / CSV Analyzer")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📂 Upload Excel / CSV")
    uploaded_files = st.sidebar.file_uploader(
        "Drag and drop file here or browse",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
    )

    if not uploaded_files:
        st.title("📊 Data Analysis Dashboard")
        st.write("Upload your Excel or CSV file in the left panel to start analyzing your data.")
        st.info("This dashboard creates KPIs, sales charts, city comparisons, correlation analysis, data previews, and downloadable reports.")
        st.markdown("#### Example columns")
        st.code("Invoice Number | Date | City | Invoice Total | Profit")
        st.markdown("<div style='text-align:center; color:#8b95a5; padding:1.25rem 0 0.5rem;'>Created by Aamir</div>", unsafe_allow_html=True)
        st.stop()

    # Read files and sheets
    datasets = {}
    for uploaded in uploaded_files:
        try:
            file_name = str(uploaded.name or "uploaded_file")
            sheets = load_uploaded_file(file_name, uploaded.getvalue())
            for sheet_name, frame in normalize_dataset_mapping(sheets).items():
                datasets[f"{file_name} — {sheet_name}"] = clean_frame(frame)
        except Exception as exc:
            file_name = str(getattr(uploaded, "name", "uploaded_file") or "uploaded_file")
            st.sidebar.error(f"{file_name}: {exc}")

    if not datasets:
        st.error("No readable data found. Please check your file.")
        st.stop()

    selected_dataset = st.sidebar.selectbox("Choose file / worksheet", list(datasets.keys()))
    source_df = datasets[selected_dataset].copy()
    if source_df.empty:
        st.warning("This worksheet is empty.")
        st.stop()

    # Identify likely columns
    columns = list(source_df.columns)
    numeric_columns = list(source_df.select_dtypes(include="number").columns)
    date_guess = find_column(columns, ["date", "day", "month", "time"])
    city_guess = find_column(columns, ["city", "location", "branch", "region"])
    sales_guess = find_column(columns, ["invoice total", "total amount", "sales", "revenue", "amount", "total"])
    profit_guess = find_column(columns, ["profit", "net income", "margin"])
    invoice_guess = find_column(columns, ["invoice number", "invoice no", "invoice id", "invoice"])

    # Convert likely date column to datetime for charting
    if date_guess is not None:
        source_df[date_guess] = pd.to_datetime(source_df[date_guess], errors="coerce", dayfirst=False)

    # Filters
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔎 Filters")
    filtered_df = source_df.copy()

    if city_guess is not None:
        city_values = filtered_df[city_guess].dropna().unique().tolist()
        chosen_cities = st.sidebar.multiselect("City", city_values, default=city_values)
        filtered_df = filtered_df[filtered_df[city_guess].isin(chosen_cities)]

    if date_guess is not None and filtered_df[date_guess].notna().any():
        min_date = filtered_df[date_guess].min().date()
        max_date = filtered_df[date_guess].max().date()
        date_range = st.sidebar.date_input("Date Range", value=(min_date, max_date))
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            filtered_df = filtered_df[
                filtered_df[date_guess].dt.date.between(start_date, end_date)
            ]

    # Column choices
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Dashboard Settings")
    if numeric_columns:
        default_sales = sales_guess if sales_guess in numeric_columns else numeric_columns[0]
        sales_col = st.sidebar.selectbox("Sales / Amount column", numeric_columns, index=numeric_columns.index(default_sales))
        profit_options = ["None"] + numeric_columns
        default_profit = profit_guess if profit_guess in numeric_columns else "None"
        profit_index = profit_options.index(default_profit) if default_profit in profit_options else 0
        profit_col = st.sidebar.selectbox("Profit column", profit_options, index=profit_index)
    else:
        sales_col = None
        profit_col = "None"

    # ---------- Header ----------
    st.markdown("# 📊 Data Analysis Dashboard")
    st.markdown("Upload your Excel or CSV file to clean, analyze and visualize your data.")
    st.caption(f"Selected dataset: {selected_dataset}")

    # ---------- KPI cards ----------
    st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
    k1, k2, k3, k4 = st.columns(4)

    if sales_col:
        total_sales = pd.to_numeric(filtered_df[sales_col], errors="coerce").sum()
        average_sale = pd.to_numeric(filtered_df[sales_col], errors="coerce").mean()
    else:
        total_sales = 0
        average_sale = float("nan")

    order_count = (
        filtered_df[invoice_guess].nunique()
        if invoice_guess is not None
        else len(filtered_df)
    )
    missing_count = int(filtered_df.isna().sum().sum())

    k1.metric("💰 Total Sales", money(total_sales))
    k2.metric("🧮 Average Sale", money(average_sale))
    k3.metric("🛒 Total Orders", f"{order_count:,}")
    k4.metric("⚠️ Missing Values", f"{missing_count:,}")

    st.markdown("---")

    # ---------- Charts ----------
    left, right = st.columns([1.15, 0.9])

    with left:
        st.markdown('<div class="section-title">📈 Monthly Sales Trend</div>', unsafe_allow_html=True)
        if date_guess is not None and sales_col is not None:
            trend_df = filtered_df.dropna(subset=[date_guess]).copy()
            if not trend_df.empty:
                trend_df["Month"] = trend_df[date_guess].dt.to_period("M").astype(str)
                monthly = trend_df.groupby("Month", as_index=False)[sales_col].sum()
                fig = px.line(monthly, x="Month", y=sales_col, markers=True)
                fig.update_layout(height=300, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title=sales_col)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No valid dates were found in the selected data.")
        else:
            st.info("Add a Date column and a numeric Sales/Amount column to show the monthly trend.")

    with right:
        st.markdown('<div class="section-title">🏙️ Sales by City</div>', unsafe_allow_html=True)
        if city_guess is not None and sales_col is not None:
            city_sales = filtered_df.groupby(city_guess, dropna=False)[sales_col].sum().reset_index()
            city_sales = city_sales.sort_values(sales_col, ascending=False).head(20)
            fig = px.bar(city_sales, x=city_guess, y=sales_col, color=city_guess)
            fig.update_layout(height=300, showlegend=False, margin=dict(l=10, r=10, t=20, b=10), xaxis_title="", yaxis_title=sales_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add a City column and a numeric Sales/Amount column to show city comparison.")

    # ---------- Correlation and preview ----------
    st.markdown("---")
    left2, right2 = st.columns([1, 1.15])

    with left2:
        st.markdown('<div class="section-title">📉 Correlation Analysis</div>', unsafe_allow_html=True)
        if sales_col is not None and profit_col != "None" and profit_col != sales_col:
            corr_data = filtered_df[[sales_col, profit_col]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(corr_data) >= 2:
                correlation = corr_data[sales_col].corr(corr_data[profit_col])
                fig = px.scatter(corr_data, x=sales_col, y=profit_col)
                if corr_data[sales_col].nunique() > 1:
                    slope = corr_data[sales_col].cov(corr_data[profit_col]) / corr_data[sales_col].var()
                    intercept = corr_data[profit_col].mean() - slope * corr_data[sales_col].mean()
                    x_limits = [corr_data[sales_col].min(), corr_data[sales_col].max()]
                    fig.add_scatter(
                        x=x_limits,
                        y=[slope * x + intercept for x in x_limits],
                        mode="lines",
                        name="OLS trendline",
                    )
                fig.update_layout(height=290, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig, use_container_width=True)
                relation = "Strong positive" if correlation >= 0.7 else "Positive" if correlation > 0.2 else "Strong negative" if correlation <= -0.7 else "Negative" if correlation < -0.2 else "Weak / no linear"
                st.metric("Correlation (r)", f"{correlation:.3f}", relation)
            else:
                st.info("Not enough valid numeric records to calculate correlation.")
        else:
            st.info("Choose a Profit column in the sidebar to compare it with Sales.")

    with right2:
        st.markdown('<div class="section-title">📋 Data Preview</div>', unsafe_allow_html=True)
        st.caption(f"Showing first 10 rows of {len(filtered_df):,} filtered records")
        st.dataframe(filtered_df.head(10), use_container_width=True, height=290)

    # ---------- Data quality ----------
    st.markdown("---")
    st.markdown('<div class="section-title">🧹 Data Quality & Cleaning</div>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    duplicate_rows = int(filtered_df.duplicated().sum())
    q1.metric("Duplicate rows", f"{duplicate_rows:,}")
    q2.metric("Rows", f"{len(filtered_df):,}")
    q3.metric("Columns", f"{len(filtered_df.columns):,}")

    quality = pd.DataFrame({
        "Column": filtered_df.columns,
        "Data Type": [str(filtered_df[c].dtype) for c in filtered_df.columns],
        "Missing Values": [int(filtered_df[c].isna().sum()) for c in filtered_df.columns],
        "Unique Values": [int(filtered_df[c].nunique(dropna=True)) for c in filtered_df.columns],
    })

    with st.expander("View missing values by column"):
        st.dataframe(quality, use_container_width=True)

    with st.expander("Find duplicate invoice numbers"):
        if invoice_guess is not None:
            inv = filtered_df[invoice_guess].astype("string").str.strip()
            dup_mask = inv.notna() & inv.ne("") & inv.duplicated(keep=False)
            dup_invoices = filtered_df.loc[dup_mask].sort_values(invoice_guess)
            st.write(f"Rows with repeated invoice numbers: **{len(dup_invoices):,}**")
            st.dataframe(dup_invoices, use_container_width=True)
        else:
            st.info("No invoice number column was detected. Rename the column to include 'Invoice Number' or select it in your source data.")

    with st.expander("Sort data A to Z"):
        sort_col = st.selectbox("Choose column to sort", columns)
        sort_ascending = st.radio("Order", ["A to Z / smallest to largest", "Z to A / largest to smallest"], horizontal=True)
        sorted_data = filtered_df.sort_values(sort_col, ascending=sort_ascending.startswith("A to Z"), na_position="last")
        st.dataframe(sorted_data.head(100), use_container_width=True)

    # ---------- Downloads ----------
    st.markdown("---")
    st.markdown('<div class="section-title">⬇️ Export Reports</div>', unsafe_allow_html=True)
    remove_duplicates = st.checkbox("Remove fully duplicated rows from downloaded cleaned data", value=False)
    export_df = filtered_df.drop_duplicates() if remove_duplicates else filtered_df.copy()

    csv_bytes = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ Download Cleaned CSV", csv_bytes, "cleaned_data.csv", "text/csv")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, sheet_name="Cleaned Data", index=False)
        quality.to_excel(writer, sheet_name="Data Quality", index=False)
        if sales_col is not None:
            export_df.select_dtypes(include="number").describe().to_excel(writer, sheet_name="Numeric Summary")
    excel_buffer.seek(0)
    st.download_button(
        "⬇️ Download Excel Report",
        excel_buffer.getvalue(),
        "data_analysis_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.caption("Note: KPI and chart values are calculated from your uploaded data and active filters. Review data types and filters before using results for official reporting.")
    st.markdown("<div style='text-align:center; color:#8b95a5; padding:1.25rem 0 0.5rem;'>Created by Aamir</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
