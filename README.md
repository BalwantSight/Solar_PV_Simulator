# **Solar PV Simulator**

## **A Digital Lab for Photovoltaic System Analysis in Germany**

This project is an interactive desktop application that provides a comprehensive simulation of photovoltaic (PV) systems for any location in Germany. It serves as a powerful tool for technicians, researchers, and solar energy enthusiasts to analyze the energy, economic, and environmental performance of a solar installation before it is built.

*(Recommendation: Replace this image with an updated screenshot of your simulator.)*

## **Key Features**

* **Flexible Location Analysis:** Simulate performance anywhere in Germany with a built-in database of major cities (including Berlin, Munich, Hamburg, Heidelberg, etc.) or through manual coordinate entry for any specific location.  
* **Extensive Hardware Database:** Provides unparalleled simulation versatility by allowing the user to select from hundreds of commercially available solar modules and inverters, sourced directly from the industry-standard NREL System Advisor Model (SAM) database.  
* **Configurable System Parameters:** Offers deep customization by allowing real-time adjustments of key design variables, including panel tilt and azimuth, system health (to model aggregate losses), and annual performance degradation.  
* **Comprehensive PV Simulation:** Utilizes the pvlib library to accurately model the annual energy yield (kWh/kWp), processing meteorological data through a complete model chain from irradiance to AC power output.  
* **In-Depth Financial & Environmental Analysis:** Goes beyond energy yield to calculate crucial metrics like payback period, annual savings, and kilograms of CO₂ saved, allowing for a complete project viability assessment.  
* **Professional Data Visualization:** Automatically generates clear, insightful plots including monthly production, daily profiles, and a detailed energy loss diagram, crucial for technical analysis and reporting.

## **Tech Stack**

* **Core Language:** Python 3.x  
* **Graphical User Interface (GUI):** CustomTkinter  
* **PV Simulation Engine:** pvlib-python  
* **Data Manipulation:** pandas  
* **Plotting & Visualization:** Matplotlib

## **Setup and Installation**

Follow these steps to set up and run the simulator on your local machine.

### **1\. Prerequisites**

Make sure you have **Python 3** installed on your system.

### **2\. Open a Terminal**

Navigate to the project's root directory (the folder containing interactive\_simulator\_09.py) in your terminal or command prompt.

### **3\. Create and Activate a Virtual Environment**

It is highly recommended to use a virtual environment to manage dependencies.

\# Create the virtual environment  
python \-m venv venv

\# Activate the environment  
\# On Windows:  
.\\venv\\Scripts\\activate  
\# On macOS/Linux:  
source venv/bin/activate

### **4\. Install Required Libraries**

Install all necessary libraries using pip.

pip install customtkinter pandas pvlib-python matplotlib Pillow

## **5\. How to Run the Simulator**

Once the setup is complete, run the simulator with the following command:

python interactive\_simulator\.py

## **Project Vision**

In the real world, a design error means lost resources. In a digital lab, it becomes a lesson that costs next to nothing. This simulator was built on that principle: to create a powerful, accessible tool for testing, validating, and optimizing PV systems before physical installation. It bridges the gap between digital modeling and real-world construction, accelerating innovation and helping to make better design decisions.

## **Author**

* **\[Pablo Elizondo Vega\]** \- \[https://www.linkedin.com/in/pablo-elizondo-vega/\] | \[https://github.com/BalwantSight\]