import os
import pandas as pd
import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
logo_icon = "📊"
for possible_name in ["logo.png", "logo.PNG", "logo.jpg", "logo.jpeg", "logo.webp"]:
    if os.path.exists(possible_name):
        logo_icon = possible_name
        break

st.set_page_config(page_title="Data File Comparison Tool", page_icon=logo_icon, layout="wide")

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

# ==========================================
# 3. HEADER SECTION
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
        st.title("File Comparison Tool")
else:
    st.title("File Comparison Tool")

st.caption("Upload two files (CSV or Excel) to compare changes, additions, and deletions.")


# Helper function to read uploaded files
def load_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    else:
        return pd.read_excel(uploaded_file)


# ==========================================
# 4. FILE UPLOADER SECTION
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Baseline File (Old/Original)")
    file1 = st.file_uploader("Upload File 1", type=["csv", "xlsx", "xls"], key="file1")

with col2:
    st.subheader("2. Target File (New/Updated)")
    file2 = st.file_uploader("Upload File 2", type=["csv", "xlsx", "xls"], key="file2")

# ==========================================
# 5. COMPARISON PROCESSOR
# ==========================================
if file1 and file2:
    try:
        df1 = load_file(file1)
        df2 = load_file(file2)

        st.markdown("---")
        st.subheader("3. Select Unique Key Column")

        # Find common columns across both files
        common_cols = list(set(df1.columns).intersection(set(df2.columns)))

        if not common_cols:
            st.error("❌ The two files do not share any column names. Please upload files with matching headers.")
        else:
            key_col = st.selectbox(
                "Select a unique identifier column to match records (e.g. Email, ID, Employee Number):",
                options=common_cols,
            )

            if st.button("🔍 Compare Files", type="primary"):
                # Ensure key values are strings for safe matching
                df1[key_col] = df1[key_col].astype(str).str.strip()
                df2[key_col] = df2[key_col].astype(str).str.strip()

                # Identify Added & Deleted Rows
                keys_1 = set(df1[key_col])
                keys_2 = set(df2[key_col])

                added_keys = keys_2 - keys_1
                removed_keys = keys_1 - keys_2
                common_keys = keys_1.intersection(keys_2)

                df_added = df2[df2[key_col].isin(added_keys)]
                df_removed = df1[df1[key_col].isin(removed_keys)]

                # Identify Modified Fields in Common Rows
                df1_common = df1[df1[key_col].isin(common_keys)].sort_values(by=key_col).reset_index(drop=True)
                df2_common = df2[df2[key_col].isin(common_keys)].sort_values(by=key_col).reset_index(drop=True)

                # Find modified columns
                compare_cols = [col for col in common_cols if col != key_col]
                
                modified_records = []
                for k in common_keys:
                    row1 = df1_common[df1_common[key_col] == k].iloc[0]
                    row2 = df2_common[df2_common[key_col] == k].iloc[0]

                    for col in compare_cols:
                        val1 = str(row1[col]) if pd.notna(row1[col]) else ""
                        val2 = str(row2[col]) if pd.notna(row2[col]) else ""

                        if val1 != val2:
                            modified_records.append({
                                key_col: k,
                                "Field": col,
                                "Original Value (File 1)": val1,
                                "New Value (File 2)": val2
                            })

                df_modified = pd.DataFrame(modified_records)

                # ==========================================
                # 6. RESULTS DASHBOARD
                # ==========================================
                st.markdown("---")
                st.header("📊 Comparison Results Summary")

                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Total File 1 Rows", len(df1))
                m2.metric("Total File 2 Rows", len(df2))
                m3.metric("🆕 Added Rows", len(df_added))
                m4.metric("❌ Removed Rows", len(df_removed))

                tab_added, tab_removed, tab_modified = st.tabs([
                    f"🆕 Added ({len(df_added)})", 
                    f"❌ Removed ({len(df_removed)})", 
                    f"✏️ Modified ({len(df_modified)})"
                ])

                # Tab 1: Added Records
                with tab_added:
                    if df_added.empty:
                        st.info("No new records were added in File 2.")
                    else:
                        st.dataframe(df_added, use_container_width=True)
                        st.download_button(
                            "📥 Export Added Records",
                            data=df_added.to_csv(index=False).encode("utf-8"),
                            file_name="added_records.csv",
                            mime="text/csv"
                        )

                # Tab 2: Removed Records
                with tab_removed:
                    if df_removed.empty:
                        st.info("No records were removed in File 2.")
                    else:
                        st.dataframe(df_removed, use_container_width=True)
                        st.download_button(
                            "📥 Export Removed Records",
                            data=df_removed.to_csv(index=False).encode("utf-8"),
                            file_name="removed_records.csv",
                            mime="text/csv"
                        )

                # Tab 3: Modified Records
                with tab_modified:
                    if df_modified.empty:
                        st.success("No differences found in overlapping records!")
                    else:
                        st.dataframe(df_modified, use_container_width=True)
                        st.download_button(
                            "📥 Export Modified Fields Summary",
                            data=df_modified.to_csv(index=False).encode("utf-8"),
                            file_name="modified_fields.csv",
                            mime="text/csv"
                        )

    except Exception as e:
        st.error(f"Error reading files: {e}")