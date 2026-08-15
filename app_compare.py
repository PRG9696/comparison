import os
import pandas as pd
import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
logo_icon = "💰"
for possible_name in ["logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "logo.webp"]:
    if os.path.exists(possible_name):
        logo_icon = possible_name
        break

st.set_page_config(page_title="Fee Comparison Tool", page_icon=logo_icon, layout="wide")

# ==========================================
# 2. HIDE ALL STREAMLIT UI, BADGES & TOOLBARS
# ==========================================
hide_st_style = """
    <style>
    /* Hide top header, main menu, decoration line, and toolbar */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}

    /* Hide standard footer, status widgets, and deploy buttons */
    footer {visibility: hidden !important;}
    [data-testid="stFooter"] {display: none !important;}
    .stDeployButton {display: none !important;}
    div[data-testid="stStatusWidget"] {display: none !important;}

    /* Hide Streamlit Cloud viewer badges, profile tag, and bottom floating overlays */
    [data-testid="stBottomFloatingContainer"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    div[class*="stAppViewer"] {display: none !important;}
    div[class*="Profile"] {display: none !important;}
    button[title="View profile"] {display: none !important;}
    a[href*="streamlit.io/user"] {display: none !important;}
    iframe[title="streamlit_app"] {height: 100vh !important;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Target columns to strictly compare
TARGET_COLUMNS = ["TERMLY", "MONTHLY", "PESB FEE", "MONTLY AFTER FEE"]

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def load_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file)

def clean_id(val):
    """Clean ID string to strip trailing .0 and whitespace."""
    if pd.isna(val):
        return ""
    val_str = str(val).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    return val_str

def clean_value(val):
    """Clean string values and parse numbers safely."""
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace(",", "").replace("$", "").replace("RM", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return val_str

# ==========================================
# 4. HEADER SECTION
# ==========================================
logo_file = None
for possible_name in ["logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "logo.webp"]:
    if os.path.exists(possible_name):
        logo_file = possible_name
        break

if logo_file:
    col_logo, col_title = st.columns([1, 6], vertical_alignment="center")
    with col_logo:
        st.image(logo_file, width=90)
    with col_title:
        st.title("Fee Comparison Tool")
else:
    st.title("Fee Comparison Tool")

st.caption("Upload two files to match records by **ID** and compare **TERMLY**, **MONTHLY**, **PESB FEE**, and **MONTLY AFTER FEE**.")


# ==========================================
# 5. FILE UPLOADER SECTION
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Baseline File (File 1)")
    file1 = st.file_uploader("Upload File 1", type=["csv", "xlsx", "xls"], key="file1")

with col2:
    st.subheader("2. Target File (File 2)")
    file2 = st.file_uploader("Upload File 2", type=["csv", "xlsx", "xls"], key="file2")

# ==========================================
# 6. COMPARISON LOGIC
# ==========================================
if file1 and file2:
    try:
        df1 = load_file(file1)
        df2 = load_file(file2)

        # Check for ID column presence
        if "ID" not in df1.columns or "ID" not in df2.columns:
            st.error("❌ Both files must contain an **'ID'** column to perform the comparison.")
        else:
            # Safely clean and format ID columns
            df1["ID"] = df1["ID"].apply(clean_id)
            df2["ID"] = df2["ID"].apply(clean_id)

            # Drop empty IDs
            df1 = df1[df1["ID"] != ""].copy()
            df2 = df2[df2["ID"] != ""].copy()

            # Deduplicate IDs to avoid index out-of-bounds
            df1 = df1.drop_duplicates(subset=["ID"], keep="first")
            df2 = df2.drop_duplicates(subset=["ID"], keep="first")

            # Identify target columns available in both files
            found_cols = [c for c in TARGET_COLUMNS if c in df1.columns and c in df2.columns]
            missing_cols = [c for c in TARGET_COLUMNS if c not in found_cols]

            if missing_cols:
                st.warning(f"⚠️ Note: The following requested column(s) were not found in both files: **{', '.join(missing_cols)}**")

            if st.button("🔍 Run Fee Comparison", type="primary", use_container_width=True):
                # Set ID as index for instant, error-free matching
                df1_indexed = df1.set_index("ID")
                df2_indexed = df2.set_index("ID")

                keys_1 = set(df1_indexed.index)
                keys_2 = set(df2_indexed.index)

                added_ids = keys_2 - keys_1
                removed_ids = keys_1 - keys_2
                common_ids = keys_1.intersection(keys_2)

                df_added = df2_indexed.loc[list(added_ids)].reset_index() if added_ids else pd.DataFrame()
                df_removed = df1_indexed.loc[list(removed_ids)].reset_index() if removed_ids else pd.DataFrame()

                # Safely compare overlapping records without using .iloc[0]
                diff_rows = []
                for id_val in common_ids:
                    row1 = df1_indexed.loc[id_val]
                    row2 = df2_indexed.loc[id_val]

                    for col in found_cols:
                        v1 = clean_value(row1[col])
                        v2 = clean_value(row2[col])

                        if isinstance(v1, float) and isinstance(v2, float):
                            diff = round(v2 - v1, 2)
                            if abs(diff) > 0.001:
                                diff_rows.append({
                                    "ID": id_val,
                                    "Field": col,
                                    "File 1 (Old)": round(v1, 2),
                                    "File 2 (New)": round(v2, 2),
                                    "Difference (File 2 - File 1)": diff
                                })
                        elif str(v1) != str(v2):
                            diff_rows.append({
                                "ID": id_val,
                                "Field": col,
                                "File 1 (Old)": v1,
                                "File 2 (New)": v2,
                                "Difference (File 2 - File 1)": "N/A"
                            })

                df_diff = pd.DataFrame(diff_rows)

                # ==========================================
                # 7. DISPLAY RESULTS
                # ==========================================
                st.markdown("---")
                st.header("📊 Comparison Results")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total Unique IDs (File 1)", len(df1_indexed))
                m2.metric("Total Unique IDs (File 2)", len(df2_indexed))
                m3.metric("🆕 Added IDs", len(df_added))
                m4.metric("❌ Removed IDs", len(df_removed))

                tab_diff, tab_added, tab_removed = st.tabs([
                    f"✏️ Discrepancies Found ({len(df_diff)})",
                    f"🆕 Added IDs ({len(df_added)})",
                    f"❌ Removed IDs ({len(df_removed)})"
                ])

                with tab_diff:
                    if df_diff.empty:
                        st.success("🎉 No differences found! All TERMLY, MONTHLY, PESB FEE, and MONTLY AFTER FEE values match perfectly.")
                    else:
                        st.write("Below are the specific IDs where **TERMLY**, **MONTHLY**, **PESB FEE**, or **MONTLY AFTER FEE** changed:")
                        st.dataframe(df_diff, use_container_width=True)

                        st.download_button(
                            "📥 Export Discrepancies Report to CSV",
                            data=df_diff.to_csv(index=False).encode("utf-8"),
                            file_name="fee_discrepancies.csv",
                            mime="text/csv"
                        )

                with tab_added:
                    if df_added.empty:
                        st.info("No new IDs were added in File 2.")
                    else:
                        st.dataframe(df_added, use_container_width=True)
                        st.download_button(
                            "📥 Export Added IDs to CSV",
                            data=df_added.to_csv(index=False).encode("utf-8"),
                            file_name="added_ids.csv",
                            mime="text/csv"
                        )

                with tab_removed:
                    if df_removed.empty:
                        st.info("No IDs were removed in File 2.")
                    else:
                        st.dataframe(df_removed, use_container_width=True)
                        st.download_button(
                            "📥 Export Removed IDs to CSV",
                            data=df_removed.to_csv(index=False).encode("utf-8"),
                            file_name="removed_ids.csv",
                            mime="text/csv"
                        )

    except Exception as e:
        st.error(f"Error processing files: {e}")
