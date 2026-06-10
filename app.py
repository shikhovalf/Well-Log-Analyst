import streamlit as st
import lasio
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import io
from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Image,
    Table,
    TableStyle
)

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# PDF HELPER FUNCTION

def fig_to_buffer(fig):
    buf = BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=300,
        bbox_inches="tight"
    )
    buf.seek(0)
    return buf

# STREAMLIT CONFIG

st.set_page_config(
    page_title="Well Log Analyst",
    layout="wide"
)

st.markdown(
    """
    <h1 style='color:#0B3D91; margin-bottom:0;'>Well Log Analyst</h1>
    <p style='color:#0B3D91; font-size:18px; font-weight:500; margin-top:5px;'>
    Integrated petrophysical analysis platform for reservoir characterization, lithology evaluation, porosity calculation and net reservoir thickness assessment from well log data
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stSidebar { background-color: #ffffff; border-right: 1px solid #ddd; }
    .stTitle { color: #2a9d8f; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---

st.sidebar.header("Well Information")

user_well = st.sidebar.text_input(
    "Well Number",
    placeholder="Enter well name"
)

user_field = st.sidebar.text_input(
    "Field Name",
    placeholder="Enter field name"
)

st.sidebar.markdown("---")
st.sidebar.header("Data Selection")
las_file = st.sidebar.file_uploader("Upload LAS File", type=['las'])

# --- UNIVERSAL FORMATION TOPS LOADER ---
st.sidebar.markdown("---")
st.sidebar.header("Formation Tops")

tops_file = st.sidebar.file_uploader(
    "Upload Well Picks (Excel, TXT, CSV)",
    type=['xlsx', 'xls', 'txt', 'csv', 'dat']
)
        
tops_to_plot = {} 
if tops_file:
    try:
                # 1. Load based on file extension
        if tops_file.name.endswith(('.xlsx', '.xls')):
            df_tops = pd.read_excel(tops_file)
        else:
                    # sep='\s+' handles the multiple spaces in TXT files
            df_tops = pd.read_csv(tops_file, sep=r'\s+', engine='python')
                # 2. Standardize column names (remove extra spaces)
        df_tops.columns = [c.strip() for c in df_tops.columns]
                
                # 3. Flexible column mapping to handle 'Surface name' vs 'Surface' + 'name'
        if 'Surface' in df_tops.columns and 'name' in df_tops.columns:
            df_tops['Full_Name'] = df_tops['Surface'] + " " + df_tops['name']
            name_col = 'Full_Name'
        elif 'Surface name' in df_tops.columns:
            name_col = 'Surface name'
        else:
                    # Fallback to the first text column found
            name_col = df_tops.select_dtypes(include=['object']).columns[0]

                # 4. Map the Depth (MD)
        depth_col = 'MD' if 'MD' in df_tops.columns else df_tops.columns[2]

                # Create the dictionary for selection
        all_tops_dict = pd.Series(df_tops[depth_col].values, index=df_tops[name_col]).to_dict()
                
                # 5. Interactive Selection Box
        selected_top_names = st.multiselect(
            "Select Tops to Display", 
            options=list(all_tops_dict.keys()),
            default=[]
        )
        tops_to_plot = {name: all_tops_dict[name] for name in selected_top_names}

    except Exception as top_err:
        st.error(f"Error loading picks: {top_err}")

if las_file:
    try:
        # 1. LOAD DATA
        bytes_data = las_file.read()
        str_io = io.StringIO(bytes_data.decode('utf-8', errors='ignore'))
        las = lasio.read(str_io)
        
        df = las.df()
        st.sidebar.subheader("Available Curves")

        curve_map = {
            "Gamma Ray": ["GR", "HGR", "GR_EDTC"],
            "Resistivity": ["RT", "RDEP", "LLD", "ILD", "HRD"],
            "Density": ["RHOB", "DEN", "ZDEN", "RHOZ"],
            "Neutron": ["NPHI", "HCNL", "NEU", "NPHI_LS"],
            "Caliper": ["CALI", "CALX", "CALS"],
            "Bit Size": ["BIT", "BS"],
            "PEF": ["PE", "PEF", "PEFZ"],
            "Compressional Sonic": ["DTC", "AC", "DT"],
            "Shear Sonic": ["DTS", "ACS", "DT_S"]
        }

        for name, aliases in curve_map.items():
            found = any(c in df.columns for c in aliases)

            if found:
                st.sidebar.markdown(f"<span style='color:green;'>✔ {name}</span>", unsafe_allow_html=True)
            else:
                st.sidebar.markdown(f"<span style='color:red;'>✖ {name}</span>", unsafe_allow_html=True)


        df.replace([-999.25, -9999, -999.0], np.nan, inplace=True)
        df = df.sort_index()

          # --- CURVE MAPPING ---
        def get_curve(df_in, aliases):
            for a in aliases:
                if a in df_in.columns: return df_in[a]
            return pd.Series(np.nan, index=df_in.index)
        
        df_clean = df.rolling(window=7, center=True).median()

        depth = df_clean.index 
        gr = get_curve(df_clean, ["HGR", "GR", "GR_EDTC"])
        res = get_curve(df_clean, ["HRD", "RDEP", "RT", "LLD", "ILD"])
        den = get_curve(df_clean, ["ZDEN", "DEN", "RHOB", "RHOZ"])
        neu = get_curve(df_clean, ["HCNL", "NPHI", "NEU", "NPHI_LS"])
        cali = get_curve(df_clean, ["CALX", "CALI", "CALS"])
        bs = get_curve(df_clean, ["BIT", "BS"])
        pef = get_curve(df_clean, ["PE", "PEF", "PEFZ"])
        dtc = get_curve(df_clean,["DTC_FINAL", "DTC", "AC", "DT"]) 
        dts = get_curve(df_clean, ["DTS_FINAL", "DTS", "ACS", "DT_S", "DTs"])

        # 2. PROCESSING
        valid = neu.dropna()

        if len(valid) > 0:

            median_val = valid.median()
            max_val = valid.max()

            fraction_like = (median_val < 1.0) and (max_val < 1.5)

            # convert ONLY if clearly fraction-like
            if fraction_like:
                neu = neu * 100
                unit_status = "converted v/v → pu (%)"
            else:
                unit_status = "pu (%)"
            st.sidebar.info(f"NPHI status: {unit_status}")
        
        df_clean["NPHI"] = neu

        df_clean["DTC_FINAL"] = dtc
        df_clean["DTS_FINAL"] = dts
        if dtc.isna().all():
            st.error("No compressional sonic curve found (DTC, AC, or DT).")
            st.stop()

        if dts.isna().all():
            st.warning("No shear sonic curve found (DTS, ACS, DT_S). Vp/Vs analysis will not be available.")

        df_clean["VPVS"] = df_clean["DTS_FINAL"] / df_clean["DTC_FINAL"]
        vp_vs = df_clean['VPVS']

        # --- SONIC UNITS ---
        st.sidebar.header("Sonic Settings")

        sonic_unit = st.sidebar.radio(
            "DTC/DTS Units",
            ["µs/ft", "µs/m"],
            index=0   # default = µs/ft
        )

        if sonic_unit == "µs/ft":
            df_clean["VP"] = 304800 / df_clean["DTC_FINAL"]   # ft/s
            df_clean["VS"] = 304800 / df_clean["DTS_FINAL"]
            velocity_unit = "ft/s"
            ai_unit = "g/cc · ft/s"
        else:
            df_clean["VP"] = 1_000_000 / df_clean["DTC_FINAL"]   # m/s
            df_clean["VS"] = 1_000_000 / df_clean["DTS_FINAL"]
            velocity_unit = "m/s"
            ai_unit = "g/cc · m/s"

          # Acoustic Impedance
        df_clean["AI"] = df_clean["VP"] * den

        vp = df_clean["VP"]
        vs = df_clean["VS"]
        ai = df_clean["AI"]

        # 3. INTERACTIVE CONTROLS
        st.sidebar.header("Visual Cutoffs")
        g_cut = st.sidebar.slider("GR Cutoff", 0, 150, 40)
        r_cut = st.sidebar.slider("Resistivity Cutoff", 0.1, 1000.0, 10.0)
        
        min_dep, max_dep = float(df_clean.index.min()), float(df_clean.index.max())
        depth_range = st.sidebar.slider("Depth Zoom", min_dep, max_dep, (min_dep, max_dep))

        # --- VSH CALCULATION ---

        st.sidebar.header("Vsh Calculation")

        gr_clean = st.sidebar.number_input(
            "Clean GR",
            0.0, 150.0, 20.0
        )
        gr_shale = st.sidebar.number_input(
            "Shale GR",
            0.0, 200.0, 120.0
        )

        vsh_method = st.sidebar.selectbox(
            "Vsh Method",
            [
                "Linear",
                "Larionov Tertiary",
                "Larionov Older",
                "Clavier",
                "Steiber"
            ]
        )

        if gr_shale <= gr_clean:
            st.error("Shale GR must be greater than Clean GR")
            vsh = pd.Series(np.nan, index=gr.index)
        else:
            igr = (gr - gr_clean) / (gr_shale - gr_clean)
            igr = igr.clip(0, 1)

        # --- VSH METHODS ---

            if vsh_method == "Linear":
                vsh = igr

            elif vsh_method == "Larionov Tertiary":
                vsh = 0.083 * (2 ** (3.7 * igr) - 1)

            elif vsh_method == "Larionov Older":
                vsh = 0.33 * (2 ** (2 * igr) - 1)

            elif vsh_method == "Clavier":
                vsh = 1.7 - np.sqrt(np.maximum(3.38 - (igr + 0.7) ** 2, 0))

            elif vsh_method == "Steiber":
                vsh = igr / (3 - 2 * igr)

            vsh = vsh.clip(0, 1)

        df_clean["VSH"] = vsh 
        
        # --- PLOTTING ---
        fig, ax = plt.subplots(nrows=1, ncols=8, figsize=(22, 12), sharey=True)
        fig.subplots_adjust(top=0.80, wspace=0.20)

        # Well Header extraction
        well_name = las.well.WELL.value if hasattr(las.well.WELL, 'value') else "UNKNOWN"
        fig.suptitle(f"WELL: {well_name}", fontsize=18, fontweight='bold', y=0.98) 

       # Well Header

        # --- Well/field header ---
        well_number = las.well.WELL.value if hasattr(las.well.WELL, 'value') else "UNKNOWN"
        field_name = las.well.FLD.value if hasattr(las.well.FLD, 'value') else "UNKNOWN"

        well_number_las = (las.well.WELL.value if hasattr(las.well.WELL, "value") else "UNKNOWN")

        field_name_las = (las.well.FLD.value if hasattr(las.well.FLD, "value") else "UNKNOWN")

        well_number = user_well if user_well.strip() else well_number_las
        field_name = user_field if user_field.strip() else field_name_las

        fig.suptitle(f"WELL: {well_number}", 
             fontsize=18, 
             fontweight='bold', 
             y=0.98) 

        header_subtext = f"Field: {field_name}"

        fig.text(0.5, 0.94, header_subtext, 
         fontsize=12, 
         ha='center', 
         style='italic', 
         color='dimgrey')

        # TRACK 1: CALI / BS
        ax[0].plot(cali, depth, color="black", lw=0.8, label='CALI')
        ax[0].plot(bs, depth, color="red", lw=1.2, ls='--', label='BS')
        ax[0].fill_betweenx(depth, bs, cali, where=(cali > bs + 0.5), color="lightgrey", alpha=0.5)
        ax[0].fill_betweenx(depth, bs, cali, where=(cali < bs), color="pink", alpha=0.5)
        ax[0].set_xlim(5, 20)
        ax[0].set_title("CALIPER/BS (IN)", pad=40)
        ax[0].yaxis.set_major_locator(ticker.MultipleLocator(50))
        ax[0].grid(True, which='major', axis='y', linewidth=0.8)
        ax[0].grid(True, which='minor', axis='y', linestyle=':', alpha=0.5)

        # TRACK 2: LITHOLOGY (GR) + DYNAMIC FILLS
        ax[1].plot(gr, depth, color="black", lw=0.6)
        ax[1].axvline(g_cut, color="black", linestyle="--", lw=1.5)
        ax[1].fill_betweenx(depth, gr, g_cut, where=(gr < g_cut), color="gold", alpha=0.8) # Sand
        ax[1].fill_betweenx(depth, g_cut, gr, where=(gr >= g_cut), color="forestgreen", alpha=0.8) # Shale
        ax[1].set_xlim(0, 150)
        ax[1].set_title("GR (API)", pad=40)

        # TRACK 3: VSH
        ax[2].plot(vsh, depth, color="black", lw=1)
        ax[2].fill_betweenx(depth, 0, vsh, color="brown", alpha=0.7)
        ax[2].fill_betweenx(depth, vsh, 1, color="gold", alpha=0.7)
        ax[2].set_xlim(0, 1)
        ax[2].set_title("VSH", pad=40)
        ax[2].grid(True, which='both', linestyle=':', alpha=0.5)

        # TRACK 4: RESISTIVITY + DYNAMIC FILL
        ax[3].semilogx(res, depth, color="red", lw=0.8)
        ax[3].axvline(r_cut, color="black", linestyle="--", linewidth=1.5)
        ax[3].fill_betweenx(depth, r_cut, res, where=(res >= r_cut), color="coral", alpha=0.5)
        ax[3].set_xlim(0.2, 2000)
        ax[3].set_title("RES (OHMM)", pad=40)
        ax[3].grid(True, which='minor', axis='x', linestyle=':', alpha=0.3)

        # TRACK 5: POROSITY (DEN/NEU)
        # Density Axis (Primary Top)
        ax[4].plot(den, depth, color="red", lw=0.8, zorder=2, label='Density')
        ax[4].set_xlim(1.95, 2.95) 
        ax[4].set_xlabel("DENSITY (G/CC)", color="red", fontsize=9, fontweight='bold')
        ax[4].xaxis.set_label_position("top")
        ax[4].xaxis.set_ticks_position("top")
        ax[4].xaxis.set_major_locator(ticker.MultipleLocator(0.2))
        ax[4].xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
        ax[4].grid(True, which='both', axis='x', linestyle=':', alpha=0.5) 

        # Neutron Axis (Secondary Top)
        ax4 = ax[4].twiny()
        ax4.plot(neu, depth, color="blue", lw=0.8, zorder=3, label='Neutron', linestyle='--')
        ax4.set_xlim(45, -15) 
        ax4.set_xlabel("NPHI (%)", color="blue", fontsize=9, fontweight='bold')
        ax4.spines["top"].set_position(("axes", 1.06)) 
        ax4.xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax4.xaxis.set_minor_locator(ticker.MultipleLocator(5))

        # Shading Logic (Gas vs Shale/Liquid)
        # Scaling NPHI to RHOB space for visual crossover alignment
        neu_scaled = 1.95 + (45 - neu) * (2.95 - 1.95) / (45 - (-15))
        ax[4].fill_betweenx(depth, den, neu_scaled, where=(neu_scaled <= den), color="grey", alpha=0.7, label='Gas/Crossover')
        ax[4].fill_betweenx(depth, den, neu_scaled, where=(neu_scaled > den), color="yellow", alpha=0.7, label='Shale/Liquid')

        # TRACK 6: MINERALOGY (PEF)
        ax[5].plot(pef, depth, color="purple", lw=1.0, label='PEF')
        ax[5].set_xlim(0, 10)
        ax[5].set_title("PEF (B/E)", fontsize=10, pad=40) 
        ax[5].xaxis.set_label_position("top")
        ax[5].xaxis.set_ticks_position("top")
        # Standard Mineral Reference Lines
        ax[5].axvline(1.81, color="gold", ls="--", alpha=0.7, lw=1)      # Sandstone
        ax[5].axvline(5.08, color="blue", ls="--", alpha=0.7, lw=1)      # Limestone
        ax[5].axvline(3.14, color="darkgreen", ls="--", alpha=0.7, lw=1) # Dolomite

        ax[5].text(0.18, 1.04, "SS", color="gold", transform=ax[5].transAxes, fontsize=9, fontweight='bold', ha='center')
        ax[5].text(0.51, 1.04, "LS", color="blue", transform=ax[5].transAxes, fontsize=9, fontweight='bold', ha='center')
        ax[5].text(0.31, 1.04, "Dol", color="darkgreen", transform=ax[5].transAxes, fontsize=9, fontweight='bold', ha='center')

        ax[5].grid(True, which='both', linestyle=':', alpha=0.5)

        # TRACK 7: SONIC (DTC & DTS) 
        ax[6].plot(dtc, depth, color="blue", lw=0.8, label="DTC")
        ax[6].plot(dts, depth, color="green", lw=0.8, label="DTS")
        ax[6].fill_betweenx(depth, dtc, dts, color="lightblue", alpha=0.4)
        ax[6].set_xlim(40, 240) 
        ax[6].set_title(f"SONIC ({sonic_unit})", fontsize=10, pad=40) 
        ax[6].text(0.2, 1.04, "DTC", color="blue", transform=ax[6].transAxes, ha='left', fontsize=10)
        ax[6].text(0.8, 1.04, "DTS", color="green", transform=ax[6].transAxes, ha='right', fontsize=10)
        ax[6].grid(True, which='both', linestyle=':', alpha=0.5)
        
        # TRACK 8: FLUID & LITHOLOGY IDENTIFICATION (Vp/Vs) 
        ax[7].plot(vp_vs, depth, color="black", lw=1.2, label='Vp/Vs')
        ax[7].set_xlim(1.5, 2.5)
        ax[7].set_title("Vp/Vs RATIO", fontsize=10, pad=40)
        ax[7].text(0.05, 1.04, "Gas", color="red", transform=ax[7].transAxes,fontsize=10)
        ax[7].text(0.25, 1.04, "Brine", color="blue", transform=ax[7].transAxes, fontsize=10)
        # GEOLOGICAL THRESHOLD LINES
        ax[7].axvline(1.60, color="red", ls="--", lw=1.5, alpha=0.9, label='Gas')
        ax[7].axvline(1.70, color="orange", ls="--", lw=1, alpha=0.7, label='Oil limit')
        ax[7].axvline(1.75, color="blue", ls="-.", lw=1, alpha=0.6, label='Brine')
        ax[7].axvline(1.90, color="brown", ls=":", lw=1.2, alpha=0.8, label='Shale/Lime')

        # Gas Zone (Yellow/Gold)
        ax[7].fill_betweenx(depth, 1.5, 1.6, color="gold", alpha=0.2)
        # Potential Oil Zone (Light Green/Orange)
        ax[7].fill_betweenx(depth, 1.6, 1.7, color="orange", alpha=0.1)
        # Brine/Shale Zone (Blue/Grey)
        ax[7].fill_betweenx(depth, 1.75, 1.85, color="blue", alpha=0.1)
        ax[7].fill_betweenx(depth, 1.90, 2.5, color="grey", alpha=0.1)

        ax[7].xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
        ax[7].grid(True, which='both', linestyle=':', alpha=0.4)
        
        for axis in ax:
            axis.set_ylim(depth_range[1], depth_range[0]) # From Sidebar
            axis.xaxis.set_ticks_position("top")
            axis.xaxis.set_label_position("top")
            axis.grid(True, linestyle=':', alpha=0.4)

        # APPLY TOPS TO PLOT
        if tops_to_plot:
            for name, depth_val in tops_to_plot.items():
                if depth_range[0] <= depth_val <= depth_range[1]:
                    for i, axis in enumerate(ax):
                        axis.axhline(y=depth_val, color="blue", linestyle="--", lw=1.5, zorder=10)
                        if i == 0:
                            axis.text(axis.get_xlim()[0] + 0.2, depth_val, f" {name}", 
                                      color="black", fontsize=10, fontweight='bold',
                                      va='bottom', ha='left',
                                      bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', pad=1))

        # FINAL FORMATTING 
        depth_top = depth_range[0]
        depth_base = depth_range[1]
        depth_span = abs(depth_base - depth_top)

        # SMART TICK ENGINE
        if depth_span <= 50:
            major_step = 5
            minor_step = 1
        elif depth_span <= 200:
            major_step = 20
            minor_step = 5
        elif depth_span <= 600:
            major_step = 50
            minor_step = 10
        else:
            major_step = 100
            minor_step = 20
        for axis in ax:
            axis.set_ylim(depth_base, depth_top)

        # TOP AXIS STYLE
            axis.xaxis.set_ticks_position("top")
            axis.xaxis.set_label_position("top")

        # DEPTH TICKS (MAIN ADDITION)
            axis.yaxis.set_major_locator(ticker.MultipleLocator(major_step))
            axis.yaxis.set_minor_locator(ticker.MultipleLocator(minor_step))
            axis.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.0f'))

        # GRID SYSTEM
            axis.grid(True, which='major', axis='y', linewidth=0.8, alpha=0.5)
            axis.grid(True, which='minor', axis='y', linestyle=':', alpha=0.25)

            axis.grid(True, axis='x', linestyle=':', alpha=0.3)

        st.header("Well Logs Display")
        st.pyplot(fig)

        # --- INTERPRETATION SECTION ---
        st.write("---")
        st.header("Petrophysical Interpretation")
        st.subheader("Select the interval")

        # 1. Scope Selection
        # This allows you to toggle between analyzing everything or one specific unit
        analysis_mode = st.radio("Analysis Scope:", ["**Zoom Range**", "**Specific Formation**"], horizontal=True)
        
        # Default values 
        start_depth, end_depth = depth_range
        analysis_label = f"Zoom Range ({start_depth:.2f} - {end_depth:.2f} MD)"
        valid_interval = False 

        if analysis_mode == "**Zoom Range**":
            valid_interval = True
            start_depth, end_depth = depth_range

            st.success("Using current Depth Zoom interval")
            st.info(f"Depth window: {start_depth:.2f} - {end_depth:.2f} m. MD")
            analysis_label = (f"Zoom Range ({start_depth:.2f} - {end_depth:.2f} MD)")

        elif analysis_mode == "**Specific Formation**":
            
            if 'all_tops_dict' not in locals():
                st.warning("Please upload a Formation Tops file to enable interval analysis.")
                valid_interval = False

            else:
                sorted_all_tops = sorted(
                    all_tops_dict.items(),
                    key=lambda x: x[1]
                )

                all_top_names = [t[0] for t in sorted_all_tops]

                fmn_col1, fmn_col2 = st.columns(2)

                with fmn_col1:
                    start_fmn = st.selectbox(
                        "**Start of Interval:**",
                        all_top_names,
                        index=0,
                        key="interp_top"
                    )
                    start_depth = all_tops_dict[start_fmn]

                with fmn_col2:
                    end_fmn = st.selectbox(
                        "**End of Interval:**",
                        all_top_names,
                        index=len(all_top_names) - 1,
                        key="interp_bot"
                    )
                    end_depth = all_tops_dict[end_fmn]

                # Validate interval
                if start_depth >= end_depth:
                    valid_interval = False
                    st.error("Invalid interval: top is deeper than bottom")
                else:
                    valid_interval = True
                    analysis_label = f"{start_fmn} → {end_fmn}"
                    st.success(f"Selected Interval: {analysis_label}")
                    st.info(f"Depth Window: {start_depth:.2f} - {end_depth:.2f} m. MD")

        # 2. Slice the data based on the chosen Scope
        if valid_interval:
            mask_depth = (df_clean.index >= start_depth) & (df_clean.index <= end_depth)

        # Create a temporary plotting dataframe for easier filtering
            df_interp = pd.DataFrame({
                'GR': gr[mask_depth],
                'VSH': vsh[mask_depth],
                'DEN': den[mask_depth],
                'NEU': neu[mask_depth],
                'VPVS': vp_vs[mask_depth],
                'VP': vp[mask_depth],
                'VS': vs[mask_depth],
                'AI': ai[mask_depth],
                'RES': res[mask_depth],
                'PEF': pef[mask_depth],
                'DTC_FINAL': dtc[mask_depth],
                'DTS': dts[mask_depth]
            }).dropna(how='all') 

        else:
            df_interp = pd.DataFrame(columns=['GR', 'VSH', 'DEN', 'NEU', 'VPVS','VP', 'VS', 'AI','RES', 'PEF', 'DTC_FINAL', 'DTS'])

        # --- VSH ANALYSIS ---

        st.subheader("Vsh Analysis")

        if not df_interp.empty and "VSH" in df_interp.columns:

            col_vsh0, col_vsh1, col_vsh2 = st.columns([0.8, 2, 1.2])
   
            # COLUMN 1 : CUTOFF SELECTION
            
            with col_vsh0:
                st.markdown("**Select Vsh Cutoff**")
                vsh_cut = st.slider(
                    "",
                    0.0,
                    1.0,
                    0.0,
                    0.01
                )
          
            # Reservoir classification based on the Vsh slider
            res_data = df_interp[df_interp['VSH'] < vsh_cut]
            non_res_data = df_interp[df_interp['VSH'] >= vsh_cut]

            #COLUMN 2: RAW VSH HISTOGRAM

            with col_vsh1:

                fig_vsh, ax_vsh = plt.subplots(figsize=(6, 2.5))

                ax_vsh.hist(df_interp["VSH"].dropna(),bins=30,color="olive",edgecolor="black",alpha=0.7)

                # Dynamic cutoff line
                ax_vsh.axvline(vsh_cut,color="red",linestyle="--",linewidth=2,label=f"Vsh Cutoff = {vsh_cut:.2f}")

                ax_vsh.set_xlim(0, 1)
                ax_vsh.xaxis.set_major_locator(
                    ticker.MultipleLocator(0.1)
                )

                ax_vsh.xaxis.set_minor_locator(
                    ticker.MultipleLocator(0.05)
                )

                ax_vsh.set_xlabel("Vsh")
                ax_vsh.set_ylabel("Count")
                ax_vsh.set_title("Vsh Distribution")

                ax_vsh.grid(True,which='major',linestyle='-',alpha=0.4)
                ax_vsh.grid(True,which='minor',linestyle=':',alpha=0.2)
                ax_vsh.legend()
                st.pyplot(fig_vsh) 

            # COLUMN 3 : STATISTICS

            with col_vsh2:

                avg_vsh = df_interp["VSH"].mean()
                p50_vsh = df_interp["VSH"].median()

                reservoir_fraction = (
                    len(res_data) / len(df_interp) * 100
                        if len(df_interp) > 0 else 0
                )

                gross_thickness = end_depth - start_depth

                reservoir_thickness = (
                gross_thickness * reservoir_fraction / 100
                )

                # INTERPRETATION TAG

                if np.isnan(avg_vsh):
                    quality = "⚪ No data"
                elif avg_vsh < 0.35 and reservoir_fraction > 60:
                    quality = "🟢 Good reservoir"
                elif avg_vsh < 0.55 and reservoir_fraction >= 40:
                    quality = "🟡 Moderate"
                else:
                    quality = "🔴 Tight / shale dominated"

                stats_table = pd.DataFrame({
                    "Property": [
                        "Interpretation",
                        "Average Vsh",
                        "Median Vsh (P50)",
                        "Gross Thickness (m)",
                        "Net Sand Thickness (m)",
                        "Sand Fraction (%)"
                    ],
                    "Value": [
                        quality,
                        f"{avg_vsh:.2f}" if not np.isnan(avg_vsh) else "N/A",
                        f"{p50_vsh:.2f}" if not np.isnan(p50_vsh) else "N/A",
                        f"{gross_thickness:.1f}",
                        f"{reservoir_thickness:.1f}",
                        f"{reservoir_fraction:.1f}"
                    ]
                })

                st.markdown("### Interval Statistics")
                st.table(stats_table)
            st.markdown("---")
                
        else:
            st.warning("No Vsh data available for selected interval.")

        st.subheader("Reservoir Classification")

        # 4. Layout for Histograms
        col1, col2 = st.columns(2)

        with col1:
            if not df_interp.empty:
                fig_hist, ax_hist = plt.subplots(figsize=(8, 5))
        
                # Plot Reservoir (Gold)
                if not res_data.empty:
                    ax_hist.hist(res_data['DEN'], bins=30, color='gold', alpha=0.7, 
                         label='Reservoir (Sand)', edgecolor='black')
        
                # Plot Non-Reservoir (Green)
                if not non_res_data.empty:
                    ax_hist.hist(non_res_data['DEN'], bins=30, color='forestgreen', alpha=0.5, 
                         label='Non-Reservoir (Shale)', edgecolor='black')
        
                ax_hist.set_xlabel("Density (g/cc)")
                ax_hist.set_ylabel("Count")
                ax_hist.set_title("Density Distribution")
                ax_hist.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
                ax_hist.xaxis.set_minor_locator(ticker.MultipleLocator(0.02))
                ax_hist.legend()
                st.pyplot(fig_hist)
            else:
                st.warning("No Density data available in this depth range.")

        with col2:
            if not df_interp.empty and not df_interp['VPVS'].isnull().all():
                fig_vp, ax_vp = plt.subplots(figsize=(8, 5))
        
                if not res_data.empty:
                    ax_vp.hist(res_data['VPVS'], bins=30, color='gold', alpha=0.7, 
                       label='Reservoir', edgecolor='black')
        
                if not non_res_data.empty:
                    ax_vp.hist(non_res_data['VPVS'], bins=30, color='forestgreen', alpha=0.5, 
                       label='Non-Reservoir', edgecolor='black')
            
                ax_vp.set_xlabel("Vp/Vs Ratio")
                ax_vp.set_ylabel("Count")
                ax_vp.set_title("Vp/Vs Distribution")
                ax_vp.xaxis.set_major_locator(ticker.MultipleLocator(0.1))
                ax_vp.xaxis.set_minor_locator(ticker.MultipleLocator(0.05))
                ax_vp.legend()
                st.pyplot(fig_vp)
            else:
                st.warning("No Vp/Vs data available (check if DTC/DTS exist).") 

        col_ai1, col_ai2 = st.columns([1, 1])

        # COLUMN 1 : AI vs Density Crossplot
        with col_ai1:

            ai_plot = df_interp.dropna(subset=["AI", "DEN"])

            if not ai_plot.empty:

                fig_ai, ax_ai = plt.subplots(figsize=(8, 5))

                # Reservoir
                ai_res = ai_plot[ai_plot["VSH"] < vsh_cut]

                # Non Reservoir
                ai_nonres = ai_plot[ai_plot["VSH"] >= vsh_cut]

                if not ai_nonres.empty:
                    ax_ai.scatter(
                        ai_nonres["DEN"],
                        ai_nonres["AI"],
                        color="forestgreen",
                        edgecolor="black",
                        alpha=0.8,
                        s=25,
                        label="Non-Reservoir"
                    )

                if not ai_res.empty:
                    ax_ai.scatter(
                        ai_res["DEN"],
                        ai_res["AI"],
                        color="gold",
                        edgecolor="black",
                        alpha=0.8,
                        s=25,
                        label="Reservoir"
                    )

                ax_ai.set_xlabel("Density (g/cc)")
                ax_ai.set_ylabel(f"Acoustic Impedance ({ai_unit})")
                ax_ai.set_title("Acoustic Impedance vs Density Cross-Plot")
                ax_ai.grid(True, alpha=0.3)
                ax_ai.legend()

                st.pyplot(fig_ai)

            else:
                st.warning("No Acoustic Impedance data available.")

        # COLUMN 2 : AVERAGES TABLE

        with col_ai2:

            ai_res = df_interp[df_interp["VSH"] < vsh_cut]
            ai_nonres = df_interp[df_interp["VSH"] >= vsh_cut]
            st.subheader("Interval Statistics")
            avg_table = pd.DataFrame({
                "Property": [
                    "Avg Density (g/cc)",
                    "Avg Vp/Vs",
                    f"Avg Acoustic Impedance ({ai_unit})",
                    "Samples"
                ],
                "Reservoir": [
                    f"{ai_res['DEN'].mean():.2f}" if not ai_res.empty else "N/A",
                    f"{ai_res['VPVS'].mean():.2f}" if not ai_res.empty else "N/A",
                    f"{ai_res['AI'].mean():,.0f}" if not ai_res.empty else "N/A",
                    len(ai_res)
                ],
                "Non-Reservoir": [
                    f"{ai_nonres['DEN'].mean():.2f}" if not ai_nonres.empty else "N/A",
                    f"{ai_nonres['VPVS'].mean():.2f}" if not ai_nonres.empty else "N/A",
                    f"{ai_nonres['AI'].mean():,.0f}" if not ai_nonres.empty else "N/A",
                    len(ai_nonres)
                ]
            })

            st.table(avg_table)

        st.markdown("---")

        st.subheader("Lithology Classification")

        # --- NEUTRON-DENSITY CROSSPLOT ---
        if not df_interp.empty and 'NEU' in df_interp.columns and 'DEN' in df_interp.columns:
    
            plot_df = df_interp.copy()

            # IMPORTANT: lithology requires both curves
            plot_df = plot_df.dropna(subset=["DEN", "NEU"])
            plot_df = plot_df[
                plot_df["NEU"].between(-5, 50) &
                plot_df["DEN"].between(1.8, 3.0)
            ]

            # --- SHALY FILTER (FIX) ---
            shale_mask = plot_df["VSH"] > vsh_cut
            plot_df = plot_df[~shale_mask]
            if not plot_df.empty:
                st.info(f"Shale intervals removed from lithology classification using Vsh > {vsh_cut}")
            else:
                st.warning("All data removed by shale filter — adjust Vsh cutoff.")
                st.stop()

            if plot_df.empty:
                st.warning("No clean lithology data after shale filtering.")
                st.stop()

        # --- LITHOLOGY LINES ---

        # Sandstone (Quartz)
            nphi_ss = [-2.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
            rhob_ss = [2.65, 2.60, 2.52, 2.44, 2.35, 2.26, 2.18, 2.09, 2.00, 1.92, 1.83]
        # Limestone (Calcite)
            nphi_ls = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0]
            rhob_ls = [2.71, 2.63, 2.54, 2.46, 2.37, 2.28, 2.19, 2.10, 2.01, 1.93]
        # Dolomite
            nphi_dol = [1.0, 6.6, 12.0, 17.6, 23.0, 28.0, 32.5, 37.0, 41.0, 45.0] 
            rhob_dol = [2.87, 2.78, 2.69, 2.60, 2.51, 2.42, 2.32, 2.23, 2.14, 2.05]

            # --- LITHOLOGY CLASSIFICATION ---

            plot_df["RHOB_SS"] = np.interp(
                plot_df["NEU"],
                nphi_ss,
                rhob_ss
            )

            plot_df["RHOB_LS"] = np.interp(
                plot_df["NEU"],
                nphi_ls,
                rhob_ls
            )

            plot_df["RHOB_DOL"] = np.interp(
                plot_df["NEU"],
                nphi_dol,
                rhob_dol
            )
            # Distance from measured density
            plot_df["DIST_SS"] = abs(plot_df["DEN"] - plot_df["RHOB_SS"])
            plot_df["DIST_LS"] = abs(plot_df["DEN"] - plot_df["RHOB_LS"])
            plot_df["DIST_DOL"] = abs(plot_df["DEN"] - plot_df["RHOB_DOL"])

            # Assign closest lithology
            plot_df["LITH"] = (
                plot_df[["DIST_SS", "DIST_LS", "DIST_DOL"]]
                .idxmin(axis=1)
                .replace({
                    "DIST_SS": "Sandstone",
                    "DIST_LS": "Limestone",
                    "DIST_DOL": "Dolomite"
                })
            )

            lith_pct = (
                plot_df["LITH"]
                .value_counts(normalize=True)
                .mul(100)
                .round(1)
            )

            dominant_lith = lith_pct.idxmax()
            dominant_pct = lith_pct.max()

        # --- PLOTTING ---
            fig_nd, ax_nd = plt.subplots(figsize=(6, 6))

        # Lithology Lines
            ax_nd.plot(nphi_ss, rhob_ss, color='#8B4513', label='Quartz Sandstone', linewidth=1.5)
            ax_nd.plot(nphi_ls, rhob_ls, color='#0000FF', label='Calcite (Limestone)', linewidth=1.5)
            ax_nd.plot(nphi_dol, rhob_dol, color='#800080', label='Dolomite', linewidth=1.5)

            # --- POROSITY LABELS ---
            for phi in range(5, 45, 5):
                for (nphi, rhob, color) in [
                (nphi_ss, rhob_ss, '#8B4513'),
                (nphi_ls, rhob_ls, '#0000FF'),
                (nphi_dol, rhob_dol, '#800080')
            ]:
                    x = phi
                    y = np.interp(phi, nphi, rhob)

            # --- ISO-POROSITY INTERPOLATION (SLB chart) ---
            rho_f = 1.0

            lith_curves = [
                ("SS", nphi_ss, rhob_ss),
                ("LS", nphi_ls, rhob_ls),
                ("DOL", nphi_dol, rhob_dol)
            ]

            for phi in range(5, 45, 5):

                phi_frac = phi / 100.0

                curve_x = []
                curve_y = []

                for lith, nphi_arr, rhob_arr in lith_curves:

                    rho_ma = {
                        "SS": 2.65,
                        "LS": 2.71,
                        "DOL": 2.87
                    }[lith]

                    # density from porosity
                    rho_b = rho_ma - phi_frac * (rho_ma - rho_f)

                    # neutron equivalent on that lithology trend
                    nphi_val = np.interp(
                        rho_b,
                        rhob_arr[::-1],
                        nphi_arr[::-1]
                    )

                    curve_x.append(nphi_val)
                    curve_y.append(rho_b)

                x_smooth = np.linspace(curve_x[0], curve_x[-1], 30)
                y_smooth = np.interp(x_smooth, curve_x, curve_y)

                ax_nd.plot(
                    x_smooth,
                    y_smooth,
                    color='black',
                    linewidth=0.8,
                    alpha=0.6
                )

                # Label at Sandstone side
                ax_nd.text(
                    curve_x[0] + 0.5,
                    curve_y[0],
                    f"{phi}",
                    fontsize=7,
                    color='black',
                    fontweight='bold'
                )

                # Label at Limestone side 
                ax_nd.text(
                    curve_x[1] + 0.5,
                    curve_y[1],
                    f"{phi}",
                    fontsize=7,
                    color='black',
                    fontweight='bold'
                )

                  # Label at Dolomite side 
                ax_nd.text(
                    curve_x[2] + 0.5,
                    curve_y[2],
                    f"{phi}",
                    fontsize=7,
                    color='black',
                    fontweight='bold'
                )
           
        # Scatter Data
            sc = ax_nd.scatter(plot_df['NEU'], plot_df['DEN'], 
                        c=plot_df['GR'], cmap='jet', s=15, alpha=0.7, 
                        edgecolors='white', linewidth=0.2, zorder=3)

            ax_nd.set_xlabel("Neutron Porosity Index (p.u.)\n(Apparent Limestone Porosity)", fontsize=9)
            ax_nd.set_ylabel("Bulk Density (g/cc)", fontsize=9)

            ax_nd.set_xlim(-5, 50)
            ax_nd.set_ylim(1.8, 3.0)
            ax_nd.invert_yaxis()

        # Major/Minor Grid
            ax_nd.grid(True, which='major', linestyle='-', alpha=0.4)
            ax_nd.minorticks_on()
            ax_nd.grid(True, which='minor', linestyle=':', alpha=0.15)

        # Colorbar & Layout
            cbar = fig_nd.colorbar(sc, ax=ax_nd, fraction=0.046, pad=0.04)
            cbar.set_label('Gamma Ray (API)', rotation=270, labelpad=15, fontsize=8)

        # Legend at bottom right
            ax_nd.legend(loc='lower right', fontsize=7)

        # Display in columns
            col1, col2 = st.columns([1.2, 1])
            with col1:
                st.pyplot(fig_nd, use_container_width=True)

            with col2:
                st.markdown("### Interval Statistics")
                st.dataframe(plot_df[['DEN', 'NEU', 'GR']].describe().iloc[1:3].round(2), use_container_width=True)

                st.markdown("---")

                lith_table = pd.DataFrame({
                    "Lithology": lith_pct.index,
                    "Percent (%)": lith_pct.values
                }).round(2)

                st.dataframe(
                    lith_table,
                    use_container_width=True,
                    hide_index=True
           )

                st.success(
                    f"Dominant Lithology: {dominant_lith} ({dominant_pct:.1f} %)"
                )
            st.markdown("---")

            st.markdown("## Porosity Calculation")

            col_p1, col_p2, col_p3 = st.columns(3)

            with col_p1:
                phi_method = st.selectbox(
                "Porosity Method",
                ["Neutron-Density", "Density", "Sonic"]
            )

            with col_p2:
                lith_mode = st.radio(
                "Matrix Model",
                ["Single Matrix"]
            )

            with col_p3:
                rho_ma_user = st.number_input("Matrix Density (ρma)", 2.0, 3.0, 2.65, key="rho_ma")

            col_p4, col_p5, col_p6 = st.columns(3)

            with col_p4:
                rho_f_user = st.number_input("Fluid Density (ρf)", 0.5, 1.5, 1.0)

            with col_p5:
                dt_ma_user = st.number_input("Matrix Δtma", 40.0, 70.0, 55.5)

            with col_p6:
                dt_f_user = st.number_input("Fluid Δtf", 150.0, 220.0, 189.0)

            calc_df = df_interp.copy()

            # Convert NPHI from porosity units (%) to fraction
            calc_df["PHI_NEU"] = calc_df["NEU"] / 100.0

            # BASIC POROSITY CALCULATIONS

            # Density porosity
            calc_df["PHI_DEN"] = (rho_ma_user - calc_df["DEN"]) / (rho_ma_user - rho_f_user)

            # Sonic porosity (Wyllie)
            if "DTC_FINAL" in df_clean.columns:
                dt_used = df_clean["DTC_FINAL"].loc[calc_df.index]
                denom = (dt_f_user - dt_ma_user)
                if denom == 0:
                    calc_df["PHI_SONIC"] = np.nan
                else:calc_df["PHI_SONIC"] = (dt_used - dt_ma_user) / denom
            else:
                calc_df["PHI_SONIC"] = np.nan

            # METHOD SELECTION ---
            if phi_method == "Density":
                calc_df["PHI_SELECTED"] = calc_df["PHI_DEN"]

            elif phi_method == "Sonic":
                calc_df["PHI_SELECTED"] = calc_df["PHI_SONIC"]

            elif phi_method == "Neutron-Density":
                calc_df["PHI_SELECTED"] = (calc_df["PHI_DEN"] + calc_df["PHI_NEU"]) / 2

            calc_df["PHI_SELECTED"] = calc_df["PHI_SELECTED"].where(
                (calc_df["PHI_SELECTED"] > 0) & (calc_df["PHI_SELECTED"] < 0.5)
            )

            # EFFECTIVE POROSITY
            calc_df["PHI_EFFECTIVE"] = calc_df["PHI_SELECTED"] * (1 - calc_df["VSH"])

            res_phi = calc_df[calc_df["VSH"] < vsh_cut]
            non_res_phi = calc_df[calc_df["VSH"] >= vsh_cut]

            with st.expander("📘 Quick Reference: Standard Matrix & Fluid Parameters"):

                st.markdown("### Standard Matrix Parameters")

                st.table(pd.DataFrame({
                    "Lithology": ["Sandstone", "Limestone", "Dolomite"],
                    "Matrix Density (ρma) [g/cc]": ["2.65", "2.71", "2.87"],
                    "Matrix Transit Time (Δtma) [µs/ft]": ["55.5", "47.5", "43.5"]
                }))

                st.markdown("### Standard Fluid Density (ρf) Values")

                st.table(pd.DataFrame({
                    "Fluid Type": [
                        "Fresh Water / Mud Filtrate",
                        "Salt Water / Brine",
                        "Oil-Based Mud (OBM) Filtrate",
                        "Gas (In-Situ)"
                ],
                    "Density (ρf) [g/cc]": [
                        "1.00",
                        "1.10",
                        "0.80–0.85",
                        "0.20–0.50"
                ],
                    "Typical Use": [
                        "Fresh-water aquifers / WBM",
                        "Saline reservoirs / high-salinity WBM",
                        "Oil-based mud systems",
                        "Uninvaded gas zones"
                    ]
                }))
                st.markdown("### Standard Fluid Transit Time (Δtf) Values")

                st.table(pd.DataFrame({
                    "Fluid Type": [
                        "Fresh Water",
                        "Salt Water (Brine)",
                        "Oil / OBM Filtrate"
                    ],
                    "Δtf (µs/ft)": [
                        "189.0",
                        "185.0",
                        "238.0"
                    ],
                    "Δtf (µs/m)": [
                        "620",
                        "607",
                        "780"
                    ]
                }))
            
            st.markdown("### Interval Statistics")
            porosity_table = pd.DataFrame({
                "Property": [
                    "Avg Total Porosity (%)",
                    "Avg Effective Porosity (%)",
                    "Samples"
                ],

                "Reservoir": [
                    f"{res_phi['PHI_SELECTED'].mean()*100:.1f}" if not res_phi.empty else "N/A",
                    f"{res_phi['PHI_EFFECTIVE'].mean()*100:.1f}" if not res_phi.empty else "N/A",
                    len(res_phi)
                ],

                "Non-Reservoir": [
                    f"{non_res_phi['PHI_SELECTED'].mean()*100:.1f}" if not non_res_phi.empty else "N/A",
                    f"{non_res_phi['PHI_EFFECTIVE'].mean()*100:.1f}" if not non_res_phi.empty else "N/A",
                    len(non_res_phi)
                ],

                "Overall": [
                    f"{calc_df['PHI_SELECTED'].mean()*100:.1f}",
                    f"{calc_df['PHI_EFFECTIVE'].mean()*100:.1f}",
                    len(calc_df)
                ]
            })

            st.table(porosity_table)

            st.markdown("---")

            st.markdown("### Net Reservoir Thickness Calculation")
            col_phi1, col_phi2, col_phi3 = st.columns([0.7, 2.3, 1])
            
            #COLUMN 1: PHIE CUTOFF
            with col_phi1:
                st.markdown("**Select Effective Porosity Cutoff (%)**")
                phi_cutoff = st.slider(
                    "",
                    0.0,
                    40.0,
                    0.0,
                    0.5
                )
            phi_cut = phi_cutoff / 100.0 

            #COLUMN 2: HISTOGRAM
            with col_phi2:

                reservoir_mask = calc_df["VSH"] < vsh_cut

                reservoir_porosity = (
                    calc_df.loc[
                    reservoir_mask,
                    "PHI_EFFECTIVE"
                    ].dropna() * 100
                )

                non_res_porosity = (
                    calc_df.loc[
                    ~reservoir_mask,
                    "PHI_EFFECTIVE"
                    ].dropna() * 100
                )

                fig_phi, ax_phi = plt.subplots(figsize=(8,4))

                if len(reservoir_porosity) > 0:
                    ax_phi.hist(
                        reservoir_porosity,
                        bins=30,
                        alpha=0.7,
                        color="gold",
                        edgecolor="black",
                        label="Reservoir"
                    )

                if len(non_res_porosity) > 0:
                    ax_phi.hist(
                        non_res_porosity,
                        bins=30,
                        alpha=0.5,
                        color="brown",
                        edgecolor="black",
                        label="Non-Reservoir"
                    )
                # 2. CUMULATIVE CURVE (RESERVOIR ONLY)
    
                ax_cdf = ax_phi.twinx()

                sorted_phi = np.sort(reservoir_porosity.values)
                cum = np.arange(len(sorted_phi)) / len(sorted_phi) * 100

                ax_cdf.plot(
                    sorted_phi,
                    cum,
                    color="black",
                    linewidth=2,
                    label="Cumulative Reservoir"
                )

                ax_cdf.set_ylabel("Cumulative % of Reservoir")

                # Porosity cutoff line
                ax_phi.axvline(
                    phi_cutoff,
                    color="red",
                    linestyle="--",
                    linewidth=2,
                    label=f"PHIE Cutoff = {phi_cutoff:.1f}%"
                )

                ax_phi.set_xlabel("Effective Porosity (%)")
                ax_phi.set_ylabel("Count")
                ax_phi.set_title(
                    f"Effective Porosity Distribution (VSH Cutoff = {vsh_cut:.2f})"
                )

                ax_phi.grid(alpha=0.3)

                ax_phi.legend(loc="upper left")
                ax_cdf.legend(loc="upper right")

                st.pyplot(fig_phi)

            #NET PAY CALCULATION

            with col_phi3:
                reservoir_zone = calc_df[
                    (calc_df["VSH"] < vsh_cut) &
                    (calc_df["PHI_EFFECTIVE"] >= phi_cut)
                ]

                net_reservoir_thickness = (
                    len(reservoir_zone) *
                    np.median(np.diff(calc_df.index))
                    if len(reservoir_zone) > 1
                    else 0
                )

                avg_reservoir_phi = (
                    reservoir_zone["PHI_EFFECTIVE"].mean() * 100
                    if len(reservoir_zone) > 0
                    else 0
                )
                st.metric(
                    "Net Reservoir Thickness",
                    f"{net_reservoir_thickness:.1f} m"
                )

                st.metric(
                    "Avg Net Reservoir Effective Porosity",
                    f"{avg_reservoir_phi:.1f}%"
                )

                # PDF REPORT GENERATION

                pdf_buffer = BytesIO()
                doc = SimpleDocTemplate(pdf_buffer)
                styles = getSampleStyleSheet()
                elements = []

                # REPORT HEADER

                elements.append(
                    Paragraph(
                        "Well Log Interpretation Report",
                        styles["Title"]
                    )
                )

                elements.append(
                    Paragraph(
                        f"Well: {well_number}",
                        styles["Normal"]
                    )
                )

                elements.append(
                    Paragraph(
                        f"Field: {field_name}",
                        styles["Normal"]
                    )
                )
                elements.append(
                    Paragraph(
                        f"Analysis Mode: {analysis_mode.replace('**','')}",
                        styles["Normal"]
                    )
                )
                elements.append(
                    Paragraph(
                        f"Depth Interval (m): {start_depth:.2f} - {end_depth:.2f}",
                        styles["Normal"]
                    )
                )

                elements.append(
                    Paragraph(
                        f"Selected Interval (m): {analysis_label}",
                        styles["Normal"]
                    )
                )

                elements.append(Spacer(1, 15))  

                # MAIN WELL LOG PANEL

                elements.append(
                    Paragraph(
                    "Well Logs Display",
                    styles["Heading1"]
                    )
                )

                elements.append(
                    Image(
                    fig_to_buffer(fig),
                    width=520,
                    height=280
                    )
                )

                elements.append(PageBreak())

                # VSH ANALYSIS

                if 'fig_vsh' in locals():

                    elements.append(
                        Paragraph(
                            "Vsh Analysis",
                            styles["Heading1"]
                        )
                    )

                    elements.append(
                        Image(
                            fig_to_buffer(fig_vsh),
                            width=420,
                            height=200
                        )
                    )

                    elements.append(Spacer(1,10))

                    if 'stats_table' in locals():

                        table_data = [stats_table.columns.tolist()]
                        table_data += stats_table.values.tolist()

                        pdf_table = Table(table_data)

                        pdf_table.setStyle(
                            TableStyle([
                                ('GRID',(0,0),(-1,-1),1,colors.black),
                                ('BACKGROUND',(0,0),(-1,0),colors.lightgrey)
                            ])
                        )

                        elements.append(pdf_table)

                    elements.append(PageBreak())

                    # RESERVOIR CLASSIFICATION

                elements.append(
                    Paragraph(
                        "Reservoir Classification",
                        styles["Heading1"]
                    )
                )

                if 'fig_hist' in locals():

                    elements.append(
                        Image(
                            fig_to_buffer(fig_hist),
                            width=420,
                            height=250
                        )
                    )
                if 'fig_vp' in locals():

                    elements.append(
                        Image(
                            fig_to_buffer(fig_vp),
                            width=420,
                            height=250
                        )
                    )

                elements.append(PageBreak())

                # AI ANALYSIS

                elements.append(
                    Paragraph(
                        "Acoustic Impedance Analysis",
                        styles["Heading1"]
                    )
                )

                if 'fig_ai' in locals():

                    elements.append(
                        Image(
                            fig_to_buffer(fig_ai),
                            width=450,
                            height=280
                        )
                    )
                if 'avg_table' in locals():

                    table_data = [avg_table.columns.tolist()]
                    table_data += avg_table.values.tolist()

                    pdf_table = Table(table_data)

                    pdf_table.setStyle(
                        TableStyle([
                            ('GRID',(0,0),(-1,-1),1,colors.black),
                            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey)
                        ])
                    )

                    elements.append(pdf_table)

                elements.append(PageBreak())

                # LITHOLOGY ANALYSIS

                elements.append(
                    Paragraph(
                        "Lithology Classification",
                        styles["Heading1"]
                    )
                )

                if 'fig_nd' in locals():

                    elements.append(
                        Image(
                            fig_to_buffer(fig_nd),
                            width=450,
                            height=450
                        )
                    )

                if 'lith_table' in locals():

                    table_data = [lith_table.columns.tolist()]
                    table_data += lith_table.values.tolist()

                    pdf_table = Table(table_data)

                    pdf_table.setStyle(
                        TableStyle([
                            ('GRID',(0,0),(-1,-1),1,colors.black),
                            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey)
                        ])
                    )

                    elements.append(pdf_table)
                    # Add dominant lithology summary
                    elements.append(Spacer(1, 10))

                    elements.append(
                        Paragraph(
                            f"<b>Dominant Lithology:</b> {dominant_lith} ({dominant_pct:.1f}%)",
                            styles["Heading2"]
                        )
                )
                elements.append(PageBreak())

                # POROSITY & NET RESERVOIR ANALYSIS

                elements.append(
                    Paragraph(
                        "Porosity Analysis",
                        styles["Heading1"]
                    )
                )

                if 'fig_phi' in locals():
                    elements.append(
                        Image(
                            fig_to_buffer(fig_phi),
                            width=450,
                            height=250
                        )
                    )
                if 'porosity_table' in locals():

                    table_data = [porosity_table.columns.tolist()]
                    table_data += porosity_table.values.tolist()

                    pdf_table = Table(table_data)

                    pdf_table.setStyle(
                        TableStyle([
                            ('GRID',(0,0),(-1,-1),1,colors.black),
                            ('BACKGROUND',(0,0),(-1,0),colors.lightgrey)
                        ])
                )

                    elements.append(pdf_table)
                elements.append(Spacer(1,10))

                elements.append(
                    Paragraph(
                        f"Net Reservoir Thickness: {net_reservoir_thickness:.1f} m",
                        styles["Heading2"]
                    )
                )

                elements.append(
                    Paragraph(
                        f"Average Net Reservoir Effective Porosity: {avg_reservoir_phi:.1f} %",
                        styles["Heading2"]
                    )
                )

                # BUILD PDF

                doc.build(elements)

                pdf_buffer.seek(0)

            st.download_button(
                label="📄 Download Complete PDF Report",
                data=pdf_buffer.getvalue(),
                file_name=f"{well_name}_Petrophysical_Report.pdf",
                mime="application/pdf"
            )

    except Exception as e:
        st.error(f"Error processing LAS file: {e}")
else:
    st.info("Upload a LAS file to start.") 

    