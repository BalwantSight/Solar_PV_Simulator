# **Technical Documentation:**

# **Solar PV Simulator**

## 

## **1\. Project Overview**

This document provides a detailed technical explanation of the Solar PV Simulator for Germany. The project's goal is to accurately model the energy, economic, and environmental performance of a grid-tied photovoltaic (PV) system. The simulation serves as a robust tool for preliminary design, optimization, and feasibility analysis, using industry-standard libraries and meteorological data.

The model is built upon the pvlib-python library, which implements a sequence of validated models to form a complete "ModelChain" from solar irradiance to AC power output.

## **2\. Detailed Features and Data Sources**

To provide a high degree of flexibility and realism, the simulator integrates several industry databases and allows the user to configure a wide range of parameters.

### **2.1. Interface and Configurable Parameters**

The graphical user interface allows full control over the simulation variables:

* **Location Selection:** The user can choose from a representative number of pre-configured German cities (Berlin, Munich, Hamburg, Heidelberg, etc.) or manually enter latitude and longitude to analyze any location.  
* **System Orientation:** The **tilt** (0-90°) and **azimuth** (0-360°) of the panels can be adjusted via intuitive sliders to find the optimal orientation.  
* **Component Selection:** The user can select specific hardware from extensive dropdown lists, which greatly increases the versatility and accuracy of the simulations.  
* **Performance and Economic Parameters:** It allows for the configuration of variables such as "System Health" (to aggregate losses), annual degradation rate, installation cost per kWp, and electricity price.

### **2.2. Integrated Data Sources**

The simulator's accuracy is based on the use of industry-standard data:

* **Meteorological Data (PVGIS):** The model automatically downloads **Typical Meteorological Year (TMY)** data from the PVGIS service. This hourly data represents the long-term average weather conditions for the selected location.  
* **Component Database (NREL SAM):** For photovoltaic modules and inverters, the simulator connects to the **System Advisor Model (SAM)** database from NREL. This provides access to hundreds of real commercial components with their complete technical specifications, enabling highly specific simulations.

### **2.3. Results Visualization and Export**

One of the project's strengths is its ability to present results in a clear and professional manner:

* **Performance Plots:** It automatically generates monthly production graphs and profiles for a sunny day.  
* **Loss Diagram:** It creates a waterfall chart that visualizes how much energy is lost at each stage of the system (DC losses, inverter losses), a standard tool in professional analysis.  
* **Economic and Environmental Graphic Analysis:** It shows the evolution of the return on investment and CO₂ saved over a 25-year period.  
* **CSV Export:** All key simulation results can be exported to a CSV file for further analysis in other tools.

## **3\. Mathematical and Simulation Model**

The simulation is executed using pvlib's ModelChain, a comprehensive class that connects all the necessary steps to model a PV system's performance.

### **3.1. The ModelChain as the Governing Model**

The core of the simulation is the pvlib.modelchain.ModelChain object. It sequentially processes meteorological data through a series of sub-models to determine the final AC power output. The key stages are:

* **Irradiance and Plane of Array (POA):** It transposes the global and direct irradiance onto the tilted plane of the panel, calculating the total available irradiance.  
* **Cell and Module Temperature:** It calculates the operating temperature of the solar cells, a critical factor for efficiency. The open\_rack model is used.  
* **DC Power Generation:** Using the POA irradiance, temperature, and the parameters of the selected module (from the SAM database), it calculates the DC power output, including Angle of Incidence (AOI) losses.  
* **Inverter Efficiency and AC Power:** The inverter model converts DC to AC power, taking its efficiency curve into account.

### **3.2. Economic and Environmental Model**

* **Annual Savings (€):** Annual Savings \= Specific Yield (kWh/kWp) \* Electricity Price (€/kWh)  
* **Payback Period (Years):** Calculated numerically by finding the point where cumulative savings (adjusted for degradation) equal the initial cost.  
* **CO₂ Saved (kg):** CO₂ Saved \= Annual Yield (kWh) \* Grid CO₂ Intensity (g/kWh) / 1000

## **4\. Model Realism & Assumptions**

* **Strengths in Realism:**  
  * **Industry-Standard Engine:** The use of pvlib ensures calculations are based on validated physical models.  
  * **Real-World Components:** Integrating the SAM database allows for simulations with commercial hardware.  
  * **TMY Data:** Using data from PVGIS provides a reliable baseline for long-term performance.  
* **Assumptions and Simplifications:**  
  * **No Shading Model:** The simulator assumes an ideal horizon with no obstructions. This is the most significant simplification.  
  * **Simplified System Losses:** Losses are aggregated into a single "System Health" control instead of being broken down.  
  * **Basic Economic Model:** It does not account for factors like inflation, O\&M costs, or different tariff structures.

## **5\. Future Improvements for Enhanced Realism**

* **Advanced Shading Analysis:** Integrate the ability to import a horizon profile file to model far-field shading.  
* **Granular Loss Modeling:** Replace the single control with individual inputs for soiling, mismatch, wiring, LID, etc.  
* **Advanced Economic Model:** Include O\&M costs, inflation, and the ability to model compensation schemes like the German EEG tariffs.  
* **System Sizing:** Add features to help calculate the optimal number of modules per string based on the inverter's voltage window.