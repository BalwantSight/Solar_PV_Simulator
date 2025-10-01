# interactive_simulator.py

import customtkinter
import pandas as pd
import pvlib
import os
import matplotlib
matplotlib.use('Agg') # Use non-interactive backend for stability
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from PIL import Image, ImageTk
import threading
import numpy as np
import time

# --- PART 1: DATA AND SIMULATION LOGIC (BACKEND) ---

GERMAN_CITIES = {
    "Berlin": (52.5200, 13.4050), "Bonn": (50.7374, 7.0982), "Bremen": (53.0793, 8.8017),
    "Cologne": (50.9375, 6.9603), "Dresden": (51.0504, 13.7373), "Düsseldorf": (51.2277, 6.7735),
    "Frankfurt": (50.1109, 8.6821), "Freiburg": (47.9990, 7.8421), "Hamburg": (53.5511, 9.9937),
    "Hannover": (52.3759, 9.7320), "Heidelberg": (49.4077, 8.6908), "Kiel": (54.3233, 10.1228),
    "Leipzig": (51.3397, 12.3731), "Munich": (48.1351, 11.5820), "Nuremberg": (49.4521, 11.0767),
    "Potsdam": (52.3906, 13.0645), "Stuttgart": (48.7758, 9.1829)
}

def get_tmy_data(latitude, longitude, city_name=None, data_folder='data'):
    """
    Downloads TMY (Typical Meteorological Year) data for a given location.
    Caches the data locally to avoid re-downloading.
    """
    os.makedirs(data_folder, exist_ok=True)
    if city_name:
        file_path = os.path.join(data_folder, f'tmy_{city_name}.csv')
    else:
        file_path = os.path.join(data_folder, f'tmy_{latitude:.4f}_{longitude:.4f}.csv')
    if os.path.exists(file_path):
        return pd.read_csv(file_path, index_col=0, parse_dates=True)
    try:
        tmy_data, _ = pvlib.iotools.get_pvgis_tmy(latitude=latitude, longitude=longitude, map_variables=True)
        tmy_data.to_csv(file_path)
        return tmy_data
    except Exception as e:
        print(f"Error downloading data: {e}")
        return None

def run_simulation(tmy_data, tilt, azimuth, lat, lon, module_name, inverter_name):
    """
    Runs the full PV simulation using pvlib's ModelChain.
    Returns: specific_yield (kWh/kWp), ac_power (W), component names, and a dictionary of loss proportions.
    """
    location = pvlib.location.Location(latitude=lat, longitude=lon, tz='Europe/Berlin')
    
    cec_modules = pvlib.pvsystem.retrieve_sam('CECMod')
    cec_inverters = pvlib.pvsystem.retrieve_sam('CECInverter')
    
    module = cec_modules[module_name]
    inverter = cec_inverters[inverter_name]
    
    system = pvlib.pvsystem.PVSystem(
        surface_tilt=tilt, 
        surface_azimuth=azimuth, 
        module_parameters=module, 
        inverter_parameters=inverter, 
        racking_model='open_rack', 
        module_type='glass_polymer'
    )
    
    mc = pvlib.modelchain.ModelChain(system, location, aoi_model='ashrae')
    mc.run_model(tmy_data)
    
    module_power_kwp = module['STC'] / 1000
    
    actual_ac_energy_kwh = mc.results.ac.sum() / 1000
    specific_yield = actual_ac_energy_kwh / module_power_kwp
    
    dc_energy_kwh = mc.results.dc['p_mp'].sum() / 1000
    
    inverter_loss_kwh = dc_energy_kwh - actual_ac_energy_kwh
    
    num_modules_per_kwp = 1000 / module['STC']
    system_area = num_modules_per_kwp * module['A_c']
    poa_energy_kwh = mc.results.effective_irradiance.sum() * system_area / 1000
    
    dc_system_loss_kwh = poa_energy_kwh - dc_energy_kwh

    # Calculate loss proportions for consistent scaling
    total_energy_input = poa_energy_kwh
    
    loss_proportions = {
        "dc_system_loss_ratio": dc_system_loss_kwh / total_energy_input,
        "inverter_loss_ratio": inverter_loss_kwh / total_energy_input,
        "final_yield_ratio": actual_ac_energy_kwh / total_energy_input
    }
    
    return specific_yield, mc.results.ac, module.name, inverter.name, loss_proportions

def create_plots(ac_power, plots_folder='results'):
    """
    Generates monthly and daily production plots.
    """
    os.makedirs(plots_folder, exist_ok=True)
    
    monthly_yield = ac_power.resample('ME').sum() / 1000
    plt.figure(figsize=(5.5, 4.5))
    monthly_yield.index = monthly_yield.index.strftime('%b')
    monthly_yield.plot(kind='bar', color='orange')
    plt.title('Monthly Production (kWh/kWp)')
    plt.ylabel('Production (kWh/kWp)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    monthly_plot_path = os.path.join(plots_folder, 'monthly_yield.png')
    plt.savefig(monthly_plot_path)
    plt.close()

    daily_power = ac_power[(ac_power.index.month == 7) & (ac_power.index.day == 15)]
    plt.figure(figsize=(5.5, 4.5))
    daily_power.plot(kind='line', color='gold')
    plt.title('Daily Profile (Sunny Day)')
    plt.ylabel('Power Output (W)')
    plt.grid(True)
    plt.tight_layout()
    daily_plot_path = os.path.join(plots_folder, 'daily_profile.png')
    plt.savefig(daily_plot_path)
    plt.close()
    
    return monthly_plot_path, daily_plot_path

def create_loss_diagram(losses, plots_folder='results'):
    """
    Generates a waterfall-style loss diagram for professional analysis.
    """
    os.makedirs(plots_folder, exist_ok=True)
    
    start = losses["POA Energy (kWh)"]
    dc_loss = losses["DC System Loss (kWh)"]
    inverter_loss = losses["Inverter Loss (kWh)"]
    final_yield = losses["Final AC Yield (kWh)"]

    labels = ['POA Energy', 'DC System Loss', 'Inverter Loss', 'Final AC Yield']
    values = [start, -dc_loss, -inverter_loss, final_yield]
    
    plt.figure(figsize=(5.5, 4.5))
    
    colors = ['#1f77b4', '#d62728', '#ff7f0e', '#2ca02c']
    
    plt.bar(labels, values, color=colors)
    
    plt.text(0, start + 50, f'{start:.0f}', ha='center', va='bottom', fontweight='bold')
    plt.text(1, start - dc_loss - 50, f'-{dc_loss:.0f}', ha='center', va='top', fontweight='bold', color='black')
    plt.text(2, start - dc_loss - inverter_loss - 50, f'-{inverter_loss:.0f}', ha='center', va='top', fontweight='bold', color='black')
    plt.text(3, final_yield + 50, f'{final_yield:.0f}', ha='center', va='bottom', fontweight='bold')

    plt.plot([0, 1], [start, start - dc_loss], color='gray', linestyle='--')
    plt.plot([1, 2], [start - dc_loss, start - dc_loss - inverter_loss], color='gray', linestyle='--')
    plt.plot([2, 3], [start - dc_loss - inverter_loss, final_yield], color='gray', linestyle='--')

    plt.title('Energy Loss Diagram (kWh per kWp)')
    plt.ylabel('Energy (kWh/kWp)')
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis='y', linestyle='--')
    plt.tight_layout()
    loss_plot_path = os.path.join(plots_folder, 'loss_diagram.png')
    plt.savefig(loss_plot_path)
    plt.close()
    return loss_plot_path

def create_economic_plot(cost, specific_yield, price, annual_degradation_rate, plots_folder='results'):
    """
    Generates a payback period analysis plot, considering degradation.
    """
    os.makedirs(plots_folder, exist_ok=True)
    
    years = np.arange(0, 26)
    
    cumulative_savings = np.zeros_like(years, dtype=float)
    current_yield = specific_yield
    
    for i in range(1, len(years)):
        annual_savings = current_yield * price
        cumulative_savings[i] = cumulative_savings[i-1] + annual_savings
        current_yield *= (1 - annual_degradation_rate)
        
    remaining_cost = cost - cumulative_savings
    
    plt.figure(figsize=(5.5, 4.5))
    plt.plot(years, remaining_cost, label='Remaining Cost', color='red')
    plt.axhline(0, color='green', linestyle='--', label='Break-even Point')
    
    payback_period = np.interp(0, -remaining_cost, years)
    
    if 0 < payback_period < 25:
        plt.plot(payback_period, 0, 'go', markersize=10, label='Payback Point')
        plt.text(payback_period, -100, f'~{payback_period:.1f} years', ha='center', color='green', fontweight='bold')
    
    plt.title('Payback Period Analysis (€/kWp)')
    plt.xlabel('Years')
    plt.ylabel('Net Cost or Savings (€/kWp)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    economic_plot_path = os.path.join(plots_folder, 'economic_plot.png')
    plt.savefig(economic_plot_path)
    plt.close()
    return economic_plot_path, payback_period

def create_environmental_plot(co2_saved_kg, plots_folder='results'):
    """
    Generates a cumulative CO₂ saved plot.
    """
    os.makedirs(plots_folder, exist_ok=True)
    
    years = np.arange(0, 26)
    cumulative_co2_saved = years * co2_saved_kg
    
    plt.figure(figsize=(5.5, 4.5))
    plt.bar(years, cumulative_co2_saved, color='green', alpha=0.7)
    plt.title('Cumulative CO₂ Saved (kg)')
    plt.xlabel('Years')
    plt.ylabel('Cumulative CO₂ Saved (kg)')
    plt.grid(True)
    plt.tight_layout()
    environmental_plot_path = os.path.join(plots_folder, 'environmental_plot.png')
    plt.savefig(environmental_plot_path)
    plt.close()
    return environmental_plot_path


# --- PART 2: GRAPHICAL USER INTERFACE (FRONTEND) ---
class SolarSimulatorApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Solar Simulator for Germany")
        self.geometry("1600x900")
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.simulation_results = None

        self.module_names = sorted(list(pvlib.pvsystem.retrieve_sam('CECMod').columns))
        self.inverter_names = sorted(list(pvlib.pvsystem.retrieve_sam('CECInverter').columns))

        self.tab_view = customtkinter.CTkTabview(self)
        self.tab_view.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # --- TAB 1: MAIN SIMULATION ---
        self.tab_view.add("Main Simulation")
        tab_1 = self.tab_view.tab("Main Simulation")
        tab_1.grid_columnconfigure(1, weight=1)
        tab_1.grid_rowconfigure(0, weight=1)

        controls_frame_1 = customtkinter.CTkFrame(tab_1, width=300)
        controls_frame_1.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        label = customtkinter.CTkLabel(controls_frame_1, text="Main Parameters", font=("Arial", 16, "bold"))
        label.pack(pady=10, padx=10)
        self.mode_selector = customtkinter.CTkSegmentedButton(controls_frame_1, values=["Select City", "Manual Entry"], command=self.toggle_mode)
        self.mode_selector.pack(pady=10, padx=20, fill="x")
        self.city_combobox = customtkinter.CTkComboBox(controls_frame_1, values=list(GERMAN_CITIES.keys()), command=self.city_selected)
        self.city_combobox.pack(pady=5, padx=20, fill="x")
        customtkinter.CTkLabel(controls_frame_1, text="Latitude (°):").pack(pady=(10,0), padx=20, anchor="w")
        self.lat_entry = customtkinter.CTkEntry(controls_frame_1)
        self.lat_entry.pack(pady=5, padx=20, fill="x")
        customtkinter.CTkLabel(controls_frame_1, text="Longitude (°):").pack(pady=(5,0), padx=20, anchor="w")
        self.lon_entry = customtkinter.CTkEntry(controls_frame_1)
        self.lon_entry.pack(pady=5, padx=20, fill="x")
        self.tilt_label = customtkinter.CTkLabel(controls_frame_1, text="Tilt: 35°")
        self.tilt_label.pack(pady=(10, 0))
        self.tilt_slider = customtkinter.CTkSlider(controls_frame_1, from_=0, to=90, number_of_steps=90, command=self.update_slider_labels)
        self.tilt_slider.pack(pady=5, padx=20, fill="x")
        self.azimuth_label = customtkinter.CTkLabel(controls_frame_1, text="Azimuth: 180° (South)")
        self.azimuth_label.pack(pady=(10, 0))
        self.azimuth_slider = customtkinter.CTkSlider(controls_frame_1, from_=0, to=360, number_of_steps=360, command=self.update_slider_labels)
        self.azimuth_slider.pack(pady=5, padx=20, fill="x")
        self.health_label = customtkinter.CTkLabel(controls_frame_1, text="System Health: 95%")
        self.health_label.pack(pady=(10, 0))
        self.health_slider = customtkinter.CTkSlider(controls_frame_1, from_=70, to=100, number_of_steps=30, command=self.update_slider_labels)
        self.health_slider.pack(pady=5, padx=20, fill="x")

        customtkinter.CTkLabel(controls_frame_1, text="Select Module:").pack(pady=(10,0), padx=20, anchor="w")
        self.module_combobox = customtkinter.CTkComboBox(controls_frame_1, values=self.module_names)
        self.module_combobox.pack(pady=5, padx=20, fill="x")

        customtkinter.CTkLabel(controls_frame_1, text="Select Inverter:").pack(pady=(10,0), padx=20, anchor="w")
        self.inverter_combobox = customtkinter.CTkComboBox(controls_frame_1, values=self.inverter_names)
        self.inverter_combobox.pack(pady=5, padx=20, fill="x")

        results_frame_1 = customtkinter.CTkFrame(tab_1)
        results_frame_1.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        results_frame_1.grid_columnconfigure(0, weight=1)
        self.yield_label = customtkinter.CTkLabel(results_frame_1, text="Annual Yield\n--- kWh/kWp", font=("Arial", 22, "bold"))
        self.yield_label.pack(pady=20, padx=20)
        self.plots_frame = customtkinter.CTkFrame(results_frame_1)
        self.plots_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.plots_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.plots_frame.grid_rowconfigure(0, weight=1)
        self.monthly_plot_label = customtkinter.CTkLabel(self.plots_frame, text="")
        self.monthly_plot_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.daily_plot_label = customtkinter.CTkLabel(self.plots_frame, text="")
        self.daily_plot_label.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        self.loss_plot_label = customtkinter.CTkLabel(self.plots_frame, text="")
        self.loss_plot_label.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")

        # --- TAB 2: ECONOMIC ANALYSIS ---
        self.tab_view.add("Economic Analysis")
        tab_2 = self.tab_view.tab("Economic Analysis")
        tab_2.grid_columnconfigure((0, 1), weight=1)

        inputs_frame_2 = customtkinter.CTkFrame(tab_2)
        inputs_frame_2.grid(row=0, column=0, padx=20, pady=20, sticky="n")
        customtkinter.CTkLabel(inputs_frame_2, text="Economic Parameters", font=("Arial", 16, "bold")).pack(pady=10, padx=10)
        customtkinter.CTkLabel(inputs_frame_2, text="Installation Cost (€/kWp):").pack(pady=(15,0), padx=20, anchor="w")
        self.cost_entry = customtkinter.CTkEntry(inputs_frame_2)
        self.cost_entry.pack(pady=5, padx=20, fill="x")
        self.cost_entry.insert(0, "1500")
        customtkinter.CTkLabel(inputs_frame_2, text="Electricity Price (€/kWh):").pack(pady=(5,0), padx=20, anchor="w")
        self.price_entry = customtkinter.CTkEntry(inputs_frame_2)
        self.price_entry.pack(pady=5, padx=20, fill="x")
        self.price_entry.insert(0, "0.30")
        # New degradation slider
        self.degradation_label = customtkinter.CTkLabel(inputs_frame_2, text="Annual Degradation: 0.5%")
        self.degradation_label.pack(pady=(10, 0))
        self.degradation_slider = customtkinter.CTkSlider(inputs_frame_2, from_=0, to=2, number_of_steps=20, command=self.update_slider_labels)
        self.degradation_slider.set(0.5)
        self.degradation_slider.pack(pady=5, padx=20, fill="x")


        results_frame_2 = customtkinter.CTkFrame(tab_2)
        results_frame_2.grid(row=0, column=1, padx=20, pady=20, sticky="n")
        customtkinter.CTkLabel(results_frame_2, text="Economic Results", font=("Arial", 16, "bold")).pack(pady=10, padx=10)
        self.savings_label = customtkinter.CTkLabel(results_frame_2, text="Annual Savings\n--- €/kWp", font=("Arial", 22, "bold"))
        self.savings_label.pack(pady=20, padx=20)
        self.payback_label = customtkinter.CTkLabel(results_frame_2, text="Payback Period\n--- Years", font=("Arial", 22, "bold"))
        self.payback_label.pack(pady=20, padx=20)
        
        self.economic_plot_label = customtkinter.CTkLabel(results_frame_2, text="")
        self.economic_plot_label.pack(pady=10, padx=10)

        # --- TAB 3: ENVIRONMENTAL IMPACT ---
        self.tab_view.add("Environmental Impact")
        tab_3 = self.tab_view.tab("Environmental Impact")
        tab_3.grid_columnconfigure((0, 1), weight=1)

        inputs_frame_3 = customtkinter.CTkFrame(tab_3)
        inputs_frame_3.grid(row=0, column=0, padx=20, pady=20, sticky="n")
        customtkinter.CTkLabel(inputs_frame_3, text="Environmental Parameters", font=("Arial", 16, "bold")).pack(pady=10, padx=10)
        customtkinter.CTkLabel(inputs_frame_3, text="Grid CO₂ Intensity (g/kWh):").pack(pady=(15,0), padx=20, anchor="w")
        self.co2_entry = customtkinter.CTkEntry(inputs_frame_3)
        self.co2_entry.pack(pady=5, padx=20, fill="x")
        self.co2_entry.insert(0, "434")

        results_frame_3 = customtkinter.CTkFrame(tab_3)
        results_frame_3.grid(row=0, column=1, padx=20, pady=20, sticky="n")
        customtkinter.CTkLabel(results_frame_3, text="Environmental Results", font=("Arial", 16, "bold")).pack(pady=10, padx=10)
        self.co2_label = customtkinter.CTkLabel(results_frame_3, text="CO₂ Saved Annually\n--- kg per kWp installed", font=("Arial", 22, "bold"))
        self.co2_label.pack(pady=20, padx=20)

        self.environmental_plot_label = customtkinter.CTkLabel(results_frame_3, text="")
        self.environmental_plot_label.pack(pady=10, padx=10)

        # --- GLOBAL ELEMENTS (OUTSIDE OF TABS) ---
        bottom_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        action_buttons_frame = customtkinter.CTkFrame(bottom_frame, fg_color="transparent")
        action_buttons_frame.pack()

        self.run_button = customtkinter.CTkButton(action_buttons_frame, text="Run Simulation", command=self.start_simulation_thread, font=("Arial", 14, "bold"))
        self.run_button.pack(side="left", pady=5, padx=10)

        self.export_button = customtkinter.CTkButton(action_buttons_frame, text="Export Results (CSV)", command=self.export_to_csv, font=("Arial", 14, "bold"), state="disabled")
        self.export_button.pack(side="left", pady=5, padx=10)
        
        self.system_details_label = customtkinter.CTkLabel(bottom_frame, text="Simulator is ready. Press 'Run Simulation'.", font=("Arial", 10))
        self.system_details_label.pack(pady=5, padx=0)
        
        self.city_combobox.set("Heidelberg")
        self.city_selected("Heidelberg")
        self.toggle_mode("Select City")
        self.tilt_slider.set(35)
        self.azimuth_slider.set(180)
        self.health_slider.set(95)
        
        # Setting common default components for a professional feel
        default_module = "Hanwha_Q_CELLS_Q_PEAK_DUO_G5_325"
        default_inverter = "SMA_America__SB3000TL_US_22__240V_"
        
        if default_module in self.module_names:
            self.module_combobox.set(default_module)
        else:
            self.module_combobox.set(self.module_names[0])
            
        if default_inverter in self.inverter_names:
            self.inverter_combobox.set(default_inverter)
        else:
            self.inverter_combobox.set(self.inverter_names[0])
        
        self.update_slider_labels()
        
    def toggle_mode(self, value):
        if value == "Select City":
            self.city_combobox.configure(state="normal")
            self.lat_entry.configure(state="disabled")
            self.lon_entry.configure(state="disabled")
        else:
            self.city_combobox.configure(state="disabled")
            self.lat_entry.configure(state="normal")
            self.lon_entry.configure(state="normal")
            
    def city_selected(self, city_name):
        lat, lon = GERMAN_CITIES[city_name]
        self.lat_entry.configure(state="normal")
        self.lon_entry.configure(state="normal")
        self.lat_entry.delete(0, "end")
        self.lat_entry.insert(0, str(lat))
        self.lon_entry.delete(0, "end")
        self.lon_entry.insert(0, str(lon))
        if self.mode_selector.get() == "Select City":
            self.lat_entry.configure(state="disabled")
            self.lon_entry.configure(state="disabled")
            
    def update_slider_labels(self, _=None):
        self.tilt_label.configure(text=f"Tilt: {int(self.tilt_slider.get())}°")
        self.azimuth_label.configure(text=f"Azimuth: {int(self.azimuth_slider.get())}° (South)")
        self.health_label.configure(text=f"System Health: {int(self.health_slider.get())}%")
        self.degradation_label.configure(text=f"Annual Degradation: {self.degradation_slider.get():.1f}%")

    def start_simulation_thread(self):
        thread = threading.Thread(target=self.run_simulation_task)
        thread.daemon = True
        thread.start()
        self.run_button.configure(state="disabled", text="Simulating...")
        
    def run_simulation_task(self):
        try:
            lat, lon = float(self.lat_entry.get()), float(self.lon_entry.get())
            tilt, azimuth = int(self.tilt_slider.get()), int(self.azimuth_slider.get())
            cost, price, co2_intensity = float(self.cost_entry.get()), float(self.price_entry.get()), float(self.co2_entry.get())
            annual_degradation_rate = self.degradation_slider.get() / 100.0
            city_name = self.city_combobox.get() if self.mode_selector.get() == "Select City" else None

            selected_module = self.module_combobox.get()
            selected_inverter = self.inverter_combobox.get()

            tmy_data = get_tmy_data(lat, lon, city_name=city_name)
            if tmy_data is not None:
                specific_yield, ac_power, module_name, inverter_name, loss_proportions = run_simulation(tmy_data, tilt, azimuth, lat, lon, selected_module, selected_inverter)
                self.after(0, self.update_gui_results, specific_yield, ac_power, cost, price, co2_intensity, module_name, inverter_name, loss_proportions, annual_degradation_rate)
        except Exception as e:
            print(f"An error occurred during simulation: {e}")
            self.after(0, self.simulation_finished, "Error")
            
    def update_gui_results(self, specific_yield, ac_power, cost, price, co2_intensity, module_name, inverter_name, loss_proportions, annual_degradation_rate):
        system_health_factor = self.health_slider.get() / 100.0
        real_specific_yield = specific_yield * system_health_factor
        
        monthly_plot_path, daily_plot_path = create_plots(ac_power * system_health_factor)
        
        # Calculate consistent losses based on the final real yield
        total_energy_input_scaled = real_specific_yield / loss_proportions['final_yield_ratio']
        dc_system_loss_scaled = total_energy_input_scaled * loss_proportions['dc_system_loss_ratio']
        inverter_loss_scaled = total_energy_input_scaled * loss_proportions['inverter_loss_ratio']

        scaled_losses = {
            "POA Energy (kWh)": total_energy_input_scaled,
            "DC System Loss (kWh)": dc_system_loss_scaled,
            "Inverter Loss (kWh)": inverter_loss_scaled,
            "Final AC Yield (kWh)": real_specific_yield,
        }

        loss_plot_path = create_loss_diagram(scaled_losses)
        
        annual_savings = real_specific_yield * price
        
        economic_plot_path, payback_period = create_economic_plot(cost, real_specific_yield, price, annual_degradation_rate)
        
        co2_saved_kg = (real_specific_yield * co2_intensity) / 1000
        environmental_plot_path = create_environmental_plot(co2_saved_kg)
        
        self.yield_label.configure(text=f"Annual Yield\n{real_specific_yield:.0f} kWh/kWp")
        self.savings_label.configure(text=f"Annual Savings\n{annual_savings:.0f} €/kWp")
        self.payback_label.configure(text=f"Payback Period\n{payback_period:.1f} Years")
        self.co2_label.configure(text=f"CO₂ Saved Annually\n{co2_saved_kg:.0f} kg per kWp installed")

        self.simulation_results = {
            "Summary": {
                "City": self.city_combobox.get() if self.mode_selector.get() == "Select City" else f"Manual ({self.lat_entry.get()}, {self.lon_entry.get()})",
                "Tilt (deg)": self.tilt_slider.get(),
                "Azimuth (deg)": self.azimuth_slider.get(),
                "System Health (%)": self.health_slider.get(),
                "Annual Degradation Rate (%)": self.degradation_slider.get(),
                "Final Annual Specific Yield (kWh/kWp)": real_specific_yield,
                "Annual Savings (EUR/kWp)": annual_savings,
                "Payback Period (Years)": payback_period,
                "Annual CO2 Saved (kg/kWp)": co2_saved_kg,
            },
            "Losses (kWh)": scaled_losses,
            "Monthly Production (kWh/kWp)": (ac_power.resample('ME').sum() / 1000) * system_health_factor,
            "Components": {"Module": module_name, "Inverter": inverter_name}
        }

        img_size = (400, 320)
        monthly_img = customtkinter.CTkImage(light_image=Image.open(monthly_plot_path), size=img_size)
        self.monthly_plot_label.configure(image=monthly_img)
        
        daily_img = customtkinter.CTkImage(light_image=Image.open(daily_plot_path), size=img_size)
        self.daily_plot_label.configure(image=daily_img)

        loss_img = customtkinter.CTkImage(light_image=Image.open(loss_plot_path), size=img_size)
        self.loss_plot_label.configure(image=loss_img)
        
        economic_img = customtkinter.CTkImage(light_image=Image.open(economic_plot_path), size=img_size)
        self.economic_plot_label.configure(image=economic_img)

        environmental_img = customtkinter.CTkImage(light_image=Image.open(environmental_plot_path), size=img_size)
        self.environmental_plot_label.configure(image=environmental_img)

        self.system_details_label.configure(text=f"Simulated Components: {module_name}  |  {inverter_name}")
        self.simulation_finished("Run Simulation")
        self.export_button.configure(state="normal")
        
    def simulation_finished(self, button_text):
        self.run_button.configure(state="normal", text=button_text)

    def export_to_csv(self):
        if not self.simulation_results:
            return
        file_path = customtkinter.filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save Simulation Results")
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='') as f:
                f.write("SIMULATION SUMMARY\n")
                summary_df = pd.DataFrame.from_dict(self.simulation_results["Summary"], orient='index', columns=['Value'])
                summary_df.to_csv(f, header=False)
                f.write("\n")

                f.write("ENERGY LOSSES (kWh)\n")
                losses_df = pd.DataFrame.from_dict(self.simulation_results["Losses (kWh)"], orient='index', columns=['Value'])
                losses_df.to_csv(f, header=False)
                f.write("\n")
                
                f.write("MONTHLY PRODUCTION (kWh per kWp)\n")
                monthly_df = self.simulation_results["Monthly Production (kWh/kWp)"].to_frame(name='Production')
                monthly_df.index = monthly_df.index.strftime('%Y-%B')
                monthly_df.to_csv(f)
                
            self.system_details_label.configure(text=f"Results successfully exported to {os.path.basename(file_path)}")
        except Exception as e:
            self.system_details_label.configure(text=f"Error exporting file: {e}")

if __name__ == "__main__":
    app = SolarSimulatorApp()
    app.mainloop()