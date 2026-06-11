# Well Log Analyst

**Well Log Analyst** is an interactive petrophysical interpretation and reservoir characterization platform built with Streamlit. 

The application provides an integrated workflow for visualizing and analyzing LAS well log data, incorporating formation tops, evaluating lithology, calculating shale volume and porosity, estimating net reservoir thickness, and generating automated PDF reports. Users can perform interval-based analysis using either the current depth zoom range or selected formation-top boundaries, enabling rapid reservoir characterization and screening within a single environment.

Designed for geoscientists, petrophysicists, reservoir engineers, and researchers, the platform combines well log visualization with quantitative interpretation tools to support efficient subsurface evaluation.

## Live Demo

### 👉 https://well-log-analyst-app.streamlit.app/
---

## 🚀 Features

### 📈 Interactive Well Log Visualization

* Multi-track well log display
* Dynamic depth zooming
* Formation tops overlay
* Automatic curve detection and mapping
* Support for multiple LAS curve naming conventions

### 🛢️ Shale Volume (Vsh) Analysis

Calculate shale volume using multiple industry-standard methods:

* Linear
* Larionov (Tertiary Rocks)
* Larionov (Older Rocks)
* Clavier
* Steiber

Features include:

* Adjustable clean sand and shale GR values
* Interactive Vsh cutoff selection
* Reservoir quality assessment
* Net sand estimation
* Vsh statistical analysis

### 💧 Porosity Evaluation

Calculate porosity using:

* Density Porosity
* Sonic Porosity (Wyllie Equation)
* Neutron-Density Porosity

Additional capabilities:

* Effective porosity calculation
* Adjustable matrix and fluid parameters
* Reservoir and non-reservoir comparison
* Porosity distribution analysis

### 🌍 Lithology Classification

Neutron-Density crossplot interpretation including:

* Sandstone, Limestone and Dolomite trends
* Dominant lithology determination
* Lithology percentage calculation
* Shale filtering using Vsh cutoff

### 📊 Reservoir Characterization

* Reservoir vs non-reservoir classification
* Net sand estimation
* Net reservoir thickness calculation
* Effective porosity cutoff analysis
* Interval-based statistics
* Reservoir quality screening

### 🎯 Rock Physics Analysis

* Compressional velocity (Vp)
* Shear velocity (Vs)
* Vp/Vs ratio analysis
* Acoustic Impedance (AI)
* Density-AI crossplot

### 📄 Automated Reporting

Generate a comprehensive PDF report including:

* Well information
* Multi-track log display
* Vsh analysis
* Reservoir classification
* Acoustic impedance analysis
* Lithology interpretation
* Porosity evaluation
* Net reservoir thickness summary

---

## 📂 Supported Input Data

### Well Log Data

Supported formats:

* `.las`

### Formation Tops

Supported formats:

* `.xlsx`
* `.xls`
* `.csv`
* `.txt`
* `.dat`

---

## 📋 Log Requirements

### Core Logs

Recommended for complete petrophysical analysis:

| Log  | Description          |
| ---- | -------------------- |
| GR   | Gamma Ray            |
| RHOB | Bulk Density         |
| NPHI | Neutron Porosity     |
| RES  | Resistivity          |
| DTC  | Compressional Sonic  |
| DTS  | Shear Sonic          |
| CALI | Caliper              |
| BS   | Bit Size             |
| PEF  | Photoelectric Factor |

### Notes

* Sonic-based workflows require DTC and/or DTS logs.
* AI and Vp/Vs calculations require sonic and density logs.
* Lithology analysis requires both density and neutron logs.

### Data Quality & Curve Recognition
- Automatic recognition of common LAS curve mnemonics
- Support for multiple vendor naming conventions
- Automatic neutron porosity unit detection and normalization
- Missing-curve identification and availability checks

### LAS Curve Recognition

The application automatically maps common industry mnemonics to standard petrophysical curves. Exact curve names are not required.

| Curve Type | Supported Mnemonics |
|------------|---------------------|
| Gamma Ray | GR, HGR, GR_EDTC |
| Resistivity | RT, RDEP, LLD, ILD, HRD |
| Density | RHOB, DEN, ZDEN, RHOZ |
| Neutron Porosity | NPHI, HCNL, NEU, NPHI_LS |
| Caliper | CALI, CALX, CALS |
| Bit Size | BIT, BS |
| Photoelectric Factor | PE, PEF, PEFZ |
| Compressional Sonic | DTC, AC, DT |
| Shear Sonic | DTS, ACS, DT_S |

---

## 📊 Analysis Workflow

### 1. Enter Well Information

Input:

* Well Number
* Field Name

Optional manual entries can override LAS header information.

### 2. Upload Data

Upload:

* LAS well log file
* Formation tops file

### 3. Visualize Logs

Review the multi-track display containing:

* Caliper / Bit Size
* Gamma Ray
* Vsh
* Resistivity
* Density-Neutron Overlay
* PEF
* Sonic
* Vp/Vs

### 4. Define Analysis Interval

Select either:

* Current depth zoom range
* Formation-top interval

### 5. Configure Vsh Parameters

Specify:

* Clean GR
* Shale GR
* Vsh calculation method

Review:

* Vsh histogram
* Net sand estimation
* Reservoir quality indicators

### 6. Reservoir Classification

Evaluate:

* Density distribution
* Vp/Vs distribution
* Acoustic impedance statistics

### 7. Lithology Analysis

Review:

* Neutron-Density crossplot
* Lithology percentages
* Dominant lithology classification

### 8. Porosity Evaluation

Select:

* Density Porosity
* Sonic Porosity
* Neutron-Density Porosity

Configure:

* Matrix density
* Fluid density
* Matrix transit time
* Fluid transit time

### 9. Net Reservoir Calculation

Define:

* Effective porosity cutoff

Calculate:

* Net reservoir thickness
* Average effective porosity

### 10. Export Report

Download a complete PDF interpretation report.

---

## 📄 PDF Report Contents

The generated report includes:

* Well information
* Analysis interval
* Multi-track well log display
* Vsh analysis
* Reservoir classification
* Acoustic impedance analysis
* Lithology interpretation
* Porosity evaluation
* Net reservoir thickness summary

---

## 🛠️ Technologies Used

* Python
* Streamlit
* Pandas
* NumPy
* Matplotlib
* LASIO
* ReportLab

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/your-username/well-log-analyst.git
cd well-log-analyst
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Application

```bash
streamlit run app.py
```

---

## 🎯 Applications

Well Log Analyst is suitable for:

* Petrophysical interpretation
* Reservoir characterization
* Formation evaluation
* Net reservoir screening
* Academic research
* Teaching and training
* Rapid well review workflows

---

## ⚠️ Disclaimer

This software is intended for educational, research, and screening purposes. Results generated by the application should be reviewed and validated by qualified petrophysical professionals before use in operational or investment decisions.

---

## 📜 License

This project is open-source and free to use for educational, research, and non-commercial purposes.
