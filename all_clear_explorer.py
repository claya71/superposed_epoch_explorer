import argparse
# import datetime
from datetime import datetime
from datetime import timedelta
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.backends.backend_tkagg
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import pickle as pkl
import tkinter as tk
import tkinter.ttk
import itertools
import memory_profiler
import logging
import config
# import download_proton_flux


# from ..utils import read_datasets as datasets
# root_logger = logging.getLogger()
# # #print(root_logger.handlers)
# # root_logger.handlers.setFormatter(logging.Formatter("%(name)s: %(message)s"))

# profiler_logstream = memory_profiler.LogFile('memory_profiler_logs', True)

"""
Tool for exploring the parameter space of the Benchmark Dataset
Made by Clayton Allison
"""






def loader(energy_channel, benchmark_list, flux_file):

    
    benchmark_df = pd.read_csv(benchmark_list, index_col = False)

    
    if energy_channel == '10.0--1':
        energy_channel_string = '>10.0 MeV 10.0 pfu'
    else:
        energy_channel_string = '>100.0 MeV 1.0 pfu'
    onlyevents = benchmark_df[benchmark_df[energy_channel_string + ' SEP Start Time'].notnull()]
    onlyevents = onlyevents[onlyevents[energy_channel_string + ' Max Flux Time'].notnull()]
    # onlyevents = onlyevents[onlyevents['Flare Magnitude'].notnull()]
    # onlyevents = onlyevents[onlyevents['DONKI CME Speed'].notnull()]
    onlyevents.reset_index(drop=True, inplace=True)

    # INITIALIZE TKINTER ROOT WINDOW
    root = tkinter.Tk()
    geometry_string = get_window_geometry(root)
    root.geometry(geometry_string)
    
    flux_df = pd.read_csv(flux_file, index_col = False)
    fluxes = flux_df[energy_channel]
    times = flux_df['dates']
    times = [datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S") for x in times]
    data = {'time': times, 'flux': fluxes}
    flux_df = pd.DataFrame(data)#, index_col=0)
    # print(df)
    flux_df = flux_df.set_index('time')
    app = ExploreApp(root, onlyevents, flux_df, energy_channel, energy_channel_string) #, list(event_labels.values()), time_buffer=datetime.timedelta(days=time_buffer), separate_energies=separate_energies)
    root.mainloop()
    app()

    return 






def clean_up_chosen_time(input_time):
    """
    Clean-up step when selecting times, we will round
    the time to the nearest 5 minutes
    """
    input_time = pd.to_datetime(input_time)
    delta_min = input_time.minute % 5

    final_time = datetime.datetime(input_time.year, input_time.month, input_time.day,
                             input_time.hour, input_time.minute - delta_min)

    return final_time


# def days_since_epoch(t):
#     # t = pytz.timezone('UTC').localize(t)
#     difference = t - config.time.epoch
#     days = difference.days + difference.seconds / 60 / 60 / 24
#     return days

# def datetime_given_days_since_epoch(days):
#     t = config.time.epoch + datetime.timedelta(days=days)
#     return t


def get_window_geometry(root):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = int(screen_width * 0.9)
    window_height = int(screen_height * 0.7)
    x_window_position = int((screen_width - window_width) / 2)
    y_window_position = int((screen_height - window_height) / 2)
    geometry_string = str(window_width) + 'x' + str(window_height) + '+' + str(x_window_position) + '+' + str(y_window_position)
    return geometry_string

class Toolbar(matplotlib.backends.backend_tkagg.NavigationToolbar2Tk):
    def __init__(self, canvas, frame, plot_click, on_click):
        super().__init__(canvas, frame)
        self.plot_click = plot_click
        self.on_click = on_click
    
    def pan(self):
        super().pan()
        if self.mode == 'pan/zoom':
            self.canvas.mpl_disconnect(self.plot_click)
        else:
            self.plot_click = self.canvas.mpl_connect('button_press_event', self.on_click)
     
    def zoom(self):
        super().zoom()
        if self.mode == 'zoom rect':
            self.canvas.mpl_disconnect(self.plot_click)
        else:
            self.plot_click = self.canvas.mpl_connect('button_press_event', self.on_click)
        




class PlaceholderEntry(tkinter.Entry):
    def __init__(self, master=None, placeholder='', **kwargs):
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.insert(0, placeholder)
        self.bind('<FocusIn>', self.on_focus_in)
        self.bind('<FocusOut>', self.on_focus_out)

    def on_focus_in(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tkinter.END)
            self.config(fg='black')
    
    def on_focus_out(self, event):
        if not self.get():
            self.insert(0, self.placeholder)
            self.config(fg='gray')

class ExploreApp:

    def __init__(self, root, onlyevents, flux_df, energy_channel, energy_channel_string):

        self.root = root
        self.flux_df = flux_df
        self.energy_channel_string = energy_channel_string
        self.fig, self.ax = plt.subplots(figsize = (20,12))
        self.root.title('Benchmark Dataset for ' + energy_channel_string)
        self.energy_channel_string = energy_channel_string
        # ESTABLISH IF ENERGIES SHOULD BE SEPARATED OR NOT
        # self.separate_energies = separate_energies

        # SET UP CLOSING PROTOCOL
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # SAVE THE EVENT SET
        self.original_df = onlyevents
        self.onlyevents = onlyevents
       

        # DEFINE THE TIME BUFFER
        # self.time_buffer = datetime.timedelta(days=1)

        # SAMPLE DATA FOR MULTIPLE PLOTS (X VALUES, Y VALUES, TITLE)
        
        self.format_event_data(flux_df, energy_channel_string, ' SEP Start Time') 
        self.yaxis_log_scale = True

        # CREATE A FRAME FOR THE PLOT
        self.plot_frame = tkinter.Frame(self.root)
        # self.plot_frame.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)
        self.plot_frame.grid(row = 0, column = 0, rowspan = 2, columnspan = 2, padx = 5, pady = 5, sticky = 'ew')

        # CREATE A FRAME FOR THE SLIDERS
        self.slider_frame = tkinter.LabelFrame(self.root, text='Options', font=(config.font.typeface, config.font.size))
      
        # self.slider_frame.pack(side=tkinter.RIGHT, fill=tkinter.BOTH, padx=2, pady=2, expand=True)
        self.slider_frame.grid(row = 0, column = 2, padx = 20, pady= 20, sticky = 'ew')
       
        

        flareclass = onlyevents['Flare Magnitude'].to_list()
        
        # input()
        self.class_label_var = tk.StringVar()
        self.class_label_var.set(f"Flare Class: >A/B") # Initial text
        self.class_value_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.class_label_var, font=(config.font.typeface, config.font.size))
        self.class_value_label.grid(row = 1, column = 0, padx = 20)

        self.slide = tk.Scale(self.slider_frame, orient='horizontal', command=self.class_label,
                           length=200,
                           tickinterval=0.5,
                           resolution = 0.5,
                           fro=-7, to=-3.5, font=('Arial',13))
        self.unimap = {'-3.5': 'X5', '-4.0':'X1', '-4.5': 'M5', '-5.0':'M1', '-5.5':'C5', '-6.0':'C1', '-6.5':'B5', '-7.0':'A/B'}
        self.slide.set(-7.0)
        self.slide.grid(row=1, column=1, padx=1, pady=1, sticky='ew')
        cmespeed = onlyevents['cmespeed'].to_list()

        # label.pack(pady=10)
        self.speed_label_var = tk.StringVar()
        self.speed_label_var.set("CME Speed: " + str(self.myround(int(min(cmespeed)), base = 50))) # Initial text
        self.speed_value_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.speed_label_var, font=(config.font.typeface, config.font.size))
        self.speed_value_label.grid(row = 2, column = 0, padx = 20)
        
        self.speed_slider = tk.Scale(
                self.slider_frame,
                from_ = int(self.myround(int(min(cmespeed)), base = 50)),
                to_ = int(self.myround(int(max(cmespeed)), base = 50)), 

                orient="horizontal",
                tickinterval = 500,
                resolution = 100,
                length = 300,
                command=self.speed_label # Link the update_label function to the slider
            )
            #  from_=int(min(cmespeed)),
                # to=int(max(cmespeed)),
        self.speed_slider.grid(row=2, column=1, padx=1, pady=1, sticky='ew')
        # label = tkinter.ttk.Label(self.speed_slider, textvariable=str(self.speed_slider.get()), font=("Helvetica", 12))
        # label.pack(pady=10)
        eventlong = onlyevents['eventlong'].to_list()
        self.long_label_var = tk.StringVar()
        self.long_label_var.set("Central Long Low Bound: 0.0") # Initial text
        self.long_value_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.long_label_var, font=(config.font.typeface, config.font.size))
        self.long_value_label.grid(row = 3, column = 0, padx = 20)
        # tkinter.ttk.Label(
        #     self.slider_frame,
        #     text="Event Longitude",
        #     font=(config.font.typeface, config.font.size)
        #     ).grid(row=2, column=0, padx=1, pady=1, sticky='e')
        self.long_slider = tk.Scale(
                self.slider_frame,
                from_=int(min(eventlong)),
                to=int(max(eventlong)),
                orient="horizontal",
                tickinterval = 50,
                resolution = 10,
                command=self.long_label # Link the update_label function to the slider
            )
        self.long_slider.grid(row=3, column=1, padx=1, pady=1, sticky='ew')


        self.long_label_high_var = tk.StringVar()
        self.long_label_high_var.set("Central Long High Bound: 50.0") # Initial text
        self.long_value_high_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.long_label_high_var, font=(config.font.typeface, config.font.size))
        self.long_value_high_label.grid(row = 4, column = 0, padx = 20)
        # tkinter.ttk.Label(
        #     self.slider_frame,
        #     text="Event Longitude",
        #     font=(config.font.typeface, config.font.size)
        #     ).grid(row=2, column=0, padx=1, pady=1, sticky='e')
        self.long_high_slider = tk.Scale(
                self.slider_frame,
                from_=int(min(eventlong)),
                to=int(max(eventlong)),
                orient="horizontal",
                tickinterval = 50,
                resolution = 10,
                command=self.long_high_label # Link the update_label function to the slider
            )
        self.long_high_slider.set(75)
        self.long_high_slider.grid(row=4, column=1, padx=1, pady=1, sticky='ew')
        # label = tkinter.ttk.Label(self.long_slider, textvariable=str(self.long_slider.get()), font=("Helvetica", 12))
        # label.pack(pady=10)
        cmewidth = self.onlyevents['cmewidth'].to_list()

        self.width_label_var = tk.StringVar()
        self.width_label_var.set("CME Width: " + str(min(cmewidth))) # Initial text
        self.width_value_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.width_label_var, font=(config.font.typeface, config.font.size))
        self.width_value_label.grid(row = 5, column = 0, padx = 20)
        # tkinter.ttk.Label(
        #     self.slider_frame,
        #     text="CME Width",
        #     font=(config.font.typeface, config.font.size)
        #     ).grid(row=3, column=0, padx=1, pady=1, sticky='e')
        self.width_slider = tk.Scale(
                self.slider_frame,
                from_=int(min(cmewidth)),
                to=int(max(cmewidth)),
                orient="horizontal",
                tickinterval = 50,
                resolution = 10,
                command=self.width_label # Link the update_label function to the slider
            )
        self.width_slider.grid(row=5, column=1, padx=1, pady=1, sticky='ew')
        # label = tkinter.ttk.Label(self.width_slider, textvariable=str(self.width_slider.get()), font=("Helvetica", 12))
        # label.pack(pady=10)
        
        # self.update_label(self.class_slider.get())
        # self.update_label(self.speed_slider.get())
        # self.update_label(self.long_slider.get())
        # self.update_label(self.width_slider.get())
        # self.slider.pack()            


        # ESTABLISH TABLE STYLE
        # tkinter.ttk.Style().configure('Treeview', font=(config.font.typeface, config.font.size - 5))
        # tkinter.ttk.Style().configure('Treeview.Heading', font=(config.font.typeface, config.font.size, 'bold')) 

        
        # ADD BUTTON FRAME
        
       

        # CREATE INITIAL PLOT
        
        
        
        self.epoch_list = [
            " Max Flux Time",
            " SEP Start Time"]
        self.epoch_str = ' SEP Start Time'
        # 2. Create a Tkinter variable and set the default value
        self.epoch_label_var = tk.StringVar()
        self.epoch_label_var.set("Set Epoch Time") # Initial text
        self.epoch_value_label = tkinter.ttk.Label(self.slider_frame, textvariable=self.epoch_label_var, font=(config.font.typeface, config.font.size))
        self.epoch_value_label.grid(row = 0, column = 0, padx = 20)
        self.epoch_var = tk.StringVar()
        self.epoch_var.set(self.epoch_list[1]) # Default value
        
        self.reset_plots()
        # 3. Create the OptionMenu widget
        # The 'command' argument binds a function to be called when the value changes
        self.dropdown_menu = tk.OptionMenu(self.slider_frame, self.epoch_var, *self.epoch_list, command=self.epoch_selection)
        self.dropdown_menu.grid(row=0, column=1, padx=1, pady=1, sticky='ew')

        self.button_frame = tkinter.Frame(self.root)
        self.button_frame.grid(row = 1, column = 2, padx = 20, pady= 20, sticky = 'ew')
        
        self.reset_button = tkinter.Button(self.button_frame, text="Reset Plots", command = self.reset_plots, font=(config.font.typeface, config.font.size))
        self.reset_button.pack(side=tkinter.LEFT, padx=(10, 0), fill=tkinter.X, expand=True)
        

    def format_event_data(self, flux_df, energy_channel_string, epoch_string):

        # starts_dt = [datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S") for x in starts]
        # epochs_dt = [datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S") for x in epochs]
        # ends_dt = [datetime.strptime(str(x), "%Y-%m-%d %H:%M:%S") for x in ends]
        self.onlyevents = self.original_df
        self.onlyevents[['t_shift', 'fluxarray', 'rise', 'decay', 'cmespeed', 'eventlong', 'width']] = None
        saved_index = []
        for index, event in self.onlyevents.iterrows():
            current_start = datetime.strptime(str(event[energy_channel_string + ' SEP Start Time']), "%Y-%m-%d %H:%M:%S")
            current_end = datetime.strptime(str(event[energy_channel_string + ' SEP End Time']), "%Y-%m-%d %H:%M:%S") 
            current_epoch = datetime.strptime(str(event[energy_channel_string + epoch_string]), "%Y-%m-%d %H:%M:%S")
            current_event = flux_df[current_start:current_end]
            current_flux = current_event['flux']
            current_times = current_event.index.to_list()
            self.onlyevents.at[index, 'rise'] = flux_df[current_start:current_epoch]['flux']
            self.onlyevents.at[index, 'decay'] = flux_df[current_epoch:current_end]['flux']
            time_since_start = []
            times = 1
            for times in range(len(current_times)):
                # print(times, current_times[times], current_times[0])
                
                tss = current_times[times] - current_times[0]
                if current_times[times] == current_epoch:
                    t_max = tss.total_seconds() / 60 / 5
                time_since_start.append(tss.total_seconds() / 60 / 5)
            
            # t_max = current_event[epochs[i]].index

            t_shift = [t - t_max for t in time_since_start] # max flux is now at sample 0
            # print(index)
            # print(self.onlyevents.iloc[index])
            self.onlyevents.at[index, 't_shift'] = t_shift

            self.onlyevents.at[index, 'fluxarray'] = current_flux
            # print(event['DONKI CME Speed'], type(event['DONKI CME Speed']), event['CDAW CME Speed'], type(event['CDAW CME Speed']))
            if pd.notnull(event['DONKI CME Speed']):
                cmespeed = event['DONKI CME Speed']
                self.onlyevents.at[index, 'cmespeed'] = cmespeed
            elif pd.notnull(event['CDAW CME Speed']):
                cmespeed = event['CDAW CME Speed']
                self.onlyevents.at[index, 'cmespeed'] = cmespeed
            else:
                # cmespeed = None
                saved_index.append(index)
                # pass
            if pd.notnull(event['DONKI CME Half Width']):
                cmewidth = 2*event['DONKI CME Half Width']
                self.onlyevents.at[index, 'cmewidth'] = cmewidth
            elif pd.notnull(event['CDAW CME Width']):
                cmewidth = event['CDAW CME Width']
                if 'Halo' in cmewidth:
                    cmewidth = 180
                elif '>' in cmewidth:
                    cmewidth = float(cmewidth[1:])
                elif type(cmewidth) == str:
                    cmewidth = float(cmewidth)
                self.onlyevents.at[index, 'cmewidth'] = cmewidth
            else:
                # cmespeed = None
                saved_index.append(index)
            if pd.notnull(event['DONKI CME Lon']):
                eventlon = event['DONKI CME Lon']
                self.onlyevents.at[index, 'eventlong'] = eventlon
            else:
                eventlon = event['Event Longitude']
                self.onlyevents.at[index, 'eventlong'] = eventlon
                # cmespeed = None
                # saved_index.append(index)
        self.onlyevents.drop(index = saved_index, inplace = True)
        
            

            
           

    def create_plot(self):
        
        
        # CREATE A NEW MATPLOTLIB FIGURE AND AXIS
        self.fig, self.ax = plt.subplots(figsize = (8,10)) # figsize=(10,6)
        self.confirmed = False
        self.current_ends = []
        # CLEAR PREVIOUS LINES IF ANY
        self.ax.clear()
        
        east_median_fit = {}
        east_rise_len = 0
        east_decay_len = 0
        central_median_fit = {}
        central_rise_len = 0
        central_decay_len = 0
        west_median_fit = {}
        west_rise_len = 0
        west_decay_len = 0
        
        # initial plotting and getting things ready for the median fits
        for index, event in self.onlyevents.iterrows():
            # print(event['t_shift'], event['fluxarray'])
     
            current_dict = {str(event[self.energy_channel_string + ' SEP Start Time']): {'flux_rise': event['rise'].to_list(), 'flux_decay': event['decay'].to_list()}}
            if event['eventlong'] <= self.long_slider.get():
                self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'red')
                east_median_fit.update(current_dict)
                if len(event['rise']) > east_rise_len:
                    east_rise_len = len(event['rise'])
                if len(event['decay'])  > east_decay_len:
                    east_decay_len = len(event['decay'])
            elif event['eventlong'] >= self.long_high_slider.get():
                self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'green')
                west_median_fit.update(current_dict)
                if len(event['rise']) > west_rise_len:
                    west_rise_len = len(event['rise'])
                if len(event['decay'])  > west_decay_len:
                    west_decay_len = len(event['decay'])
            else:
                self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'blue')
                central_median_fit.update(current_dict)
                if len(event['rise']) > central_rise_len:
                    central_rise_len = len(event['rise'])
                if len(event['decay'])  > central_decay_len:
                    central_decay_len = len(event['decay'])
            # self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.5, color = 'blue')

        self.ax.plot(0, 0, color = 'green', alpha = 1, label = 'West')
        self.ax.plot(0, 0, color = 'blue', alpha = 1, label = 'Central')
        self.ax.plot(0, 0, color = 'red', alpha = 1, label = 'East')
        
        rises = []
        decays = []
        for events in central_median_fit:
            event_datetime = datetime.strptime(events, "%Y-%m-%d %H:%M:%S")
            current_event = central_median_fit[events]
            # print(current_event)
            
            # print(current_flux)
            rise = current_event['flux_rise']
            

            # print(len(rise), max_len_rise)
            while len(rise) < central_rise_len:
                rise.insert(0, 0)
           
            decay = current_event['flux_decay']
            
            # print(len(decay), max_len_decay)
            while len(decay) < central_decay_len:
                decay.append(0)
         
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
 
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'black', label = 'Central Median Fit (N=' + str(len(central_median_fit)) + ')')
        
        rises = []
        decays = []
        for events in east_median_fit:
        
            current_event = east_median_fit[events]
            rise = current_event['flux_rise']
            while len(rise) < east_rise_len:
                rise.insert(0, 0)
            decay = current_event['flux_decay']
            while len(decay) < east_decay_len:
                decay.append(0)
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'orange', label = 'East Median Fit (N=' + str(len(east_median_fit)) + ')')
        
        rises = []
        decays = []
        for events in west_median_fit:
        
            current_event = west_median_fit[events]
            rise = current_event['flux_rise']
            while len(rise) < west_rise_len:
                rise.insert(0, 0)
            decay = current_event['flux_decay']
            while len(decay) < west_decay_len:
                decay.append(0)
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'purple', label = 'West Median Fit (N=' + str(len(west_median_fit)) +  ')')
        
        # self.ax.plot(temp_decay, median_decay, color = 'blue', label = 'Central')
        


        # ENABLE GRIDLINES
        self.ax.grid(True)
       
        
        # ADD x LABEL
        self.ax.set_xlabel('Normalized Time')
        
        # ADD y LABEL
      
        self.ax.set_ylabel('Integral Proton Flux [cm$^\\mathregular{-2}$ sr$^\\mathregular{-1}$ s$^\\mathregular{-1}$]')
        
        # EMBED THE PLOT IN THE TKINTER WINDOW
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()  # REMOVE THE OLD CANVAS IF IT EXISTS
        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
    

        # SET Y-AXIS SCALE BASED ON CURRENT STATE
        self.ax.set_yscale('log')
        self.ax.legend()
        
    def update_plots(self):
        # self.fig, self.ax = plt.subplots(figsize = (10,10))
        self.ax.clear()
        east_median_fit = {}
        east_rise_len = 0
        east_decay_len = 0
        central_median_fit = {}
        central_rise_len = 0
        central_decay_len = 0
        west_median_fit = {}
        west_rise_len = 0
        west_decay_len = 0
        for index, event in self.onlyevents.iterrows():
            current_dict = {str(event[self.energy_channel_string + ' SEP Start Time']): {'flux_rise': event['rise'].to_list(), 'flux_decay': event['decay'].to_list()}}
            # print(self.speed_slider.get(), event['cmespeed'])
            if event['cmespeed'] >= self.speed_slider.get():
                # print(self.speed_slider.get(), event['cmespeed'])
                if event['cmewidth'] >= self.width_slider.get():
                    if event['Flare Magnitude'] >= 10**(self.slide.get()) or pd.isnull(event['Flare Magnitude']):
                        if event['eventlong'] <= self.long_slider.get():
                            self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'red')
                            east_median_fit.update(current_dict)
                            if len(event['rise']) > east_rise_len:
                                east_rise_len = len(event['rise'])
                            if len(event['decay'])  > east_decay_len:
                                east_decay_len = len(event['decay'])
                        elif event['eventlong'] >= self.long_high_slider.get():
                            self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'green')
                            west_median_fit.update(current_dict)
                            if len(event['rise']) > west_rise_len:
                                west_rise_len = len(event['rise'])
                            if len(event['decay'])  > west_decay_len:
                                west_decay_len = len(event['decay'])
                        else:
                            self.ax.plot(event['t_shift'], event['fluxarray'], linewidth=1, alpha = 0.25, color = 'blue')
                            central_median_fit.update(current_dict)
                            if len(event['rise']) > central_rise_len:
                                central_rise_len = len(event['rise'])
                            if len(event['decay'])  > central_decay_len:
                                central_decay_len = len(event['decay'])
            
        self.ax.plot(0, 0, color = 'green', alpha = 1, label = 'West')
        self.ax.plot(0, 0, color = 'blue', alpha = 1, label = 'Central')
        self.ax.plot(0, 0, color = 'red', alpha = 1, label = 'East')
        
        rises = []
        decays = []
        for events in central_median_fit:
        
            current_event = central_median_fit[events]
            rise = current_event['flux_rise']
            while len(rise) < central_rise_len:
                rise.insert(0, 0)
            decay = current_event['flux_decay']
            while len(decay) < central_decay_len:
                decay.append(0)
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'black', label = 'Central Median Fit (N=' + str(len(central_median_fit)) + ')')
        rises = []
        decays = []
        for events in east_median_fit:
        
            current_event = east_median_fit[events]
            rise = current_event['flux_rise']
            while len(rise) < east_rise_len:
                rise.insert(0, 0)
            decay = current_event['flux_decay']
            while len(decay) < east_decay_len:
                decay.append(0)
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'orange', label = 'East Median Fit (N=' + str(len(east_median_fit)) + ')')
        rises = []
        decays = []
        for events in west_median_fit:
        
            current_event = west_median_fit[events]
            rise = current_event['flux_rise']
            while len(rise) < west_rise_len:
                rise.insert(0, 0)
            decay = current_event['flux_decay']
            while len(decay) < west_decay_len:
                decay.append(0)
            rises.append(rise)
            decays.append(decay)
        median_rise = [np.median(x) for x in zip(*rises)]
        median_decay = [np.median(x) for x in zip(*decays)] 
        temp_rise = []
        temp_decay = []
        for i in range(len(median_rise)):
            temp_rise.append(i - len(median_rise))
        for i in range(len(median_decay)):
            temp_decay.append(i)
        median = [*median_rise, *median_decay]
        temp = [*temp_rise, *temp_decay]
        self.ax.plot(temp, median, color = 'purple', label = 'West Median Fit (N=' + str(len(west_median_fit)) +  ')')

        # ENABLE GRIDLINES
        self.ax.grid(True)
       
        
        # ADD x LABEL
        self.ax.set_xlabel('Normalized Time')
        
        # ADD y LABEL
      
        self.ax.set_ylabel('Integral Proton Flux [cm$^\\mathregular{-2}$ sr$^\\mathregular{-1}$ s$^\\mathregular{-1}$]')
        
        # EMBED THE PLOT IN THE TKINTER WINDOW
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()  # REMOVE THE OLD CANVAS IF IT EXISTS
        self.canvas = matplotlib.backends.backend_tkagg.FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=True)
    

        # SET Y-AXIS SCALE BASED ON CURRENT STATE
        self.ax.set_yscale('log')
        self.ax.legend()
        self.canvas.draw()
   
    def epoch_selection(self, epoch_str):
        """Callback function to print the selected value dynamically."""
        self.format_event_data(self.flux_df, self.energy_channel_string, epoch_str)
        print("Selected value:", epoch_str)
        self.update_plots()
        self.epoch_str = epoch_str
    
    # def setValue(self, val):
    #     self.number = (10**(int(val)))
        
    #     # self.text.configure(text='10%s' %(self.unimap[val]))
    #     self.text.configure(f"Flare Class: {self.unimap[val]}")

    def class_label(self, value):
        """Callback function to update the label's text."""
        # Convert the value (which is a string by default from the command callback)
        # to a float, round it, and update the StringVar
        # current_value = round(float(value), 1)
        # self.class_slider.config(command=lambda e: self.class_value_label.config(text=f"Flare Class: {10**(current_value/10):.2f}"))
        # self.class_label_var.set(f"Flare Class: {10**(float(value)/10):.2f}")
        self.class_label_var.set(f"Flare Class: > {self.unimap[value]}")
        self.update_plots()

    def long_label(self, value):
        """Callback function to update the label's text."""
        # Convert the value (which is a string by default from the command callback)
        # to a float, round it, and update the StringVar
        current_value = str(self.myround(int(float(value))))
        self.long_label_var.set(f"Central Long Low Bound: {current_value}")
        self.update_plots()

    def long_high_label(self, value):
        """Callback function to update the label's text."""
        # Convert the value (which is a string by default from the command callback)
        # to a float, round it, and update the StringVar
        current_value = str(self.myround(int(float(value))))
        self.long_label_high_var.set(f"Central Long High Bound: {current_value}")
        self.update_plots()
    
    def speed_label(self, value):
        """Callback function to update the label's text."""
        # Convert the value (which is a string by default from the command callback)
        # to a float, round it, and update the StringVar
        current_value = str(self.myround(int(float(value)), base = 50))
        self.speed_label_var.set(f"CME Speed: {current_value}")
        self.update_plots()
    
    def width_label(self, value):
        """Callback function to update the label's text."""
        # Convert the value (which is a string by default from the command callback)
        # to a float, round it, and update the StringVar
        current_value = str(self.myround(int(float(value))))
        self.width_label_var.set(f"CME Width: {current_value}")
        self.update_plots()
   
    def myround(self, x, base=5):
        return base * round(x/base)

    def on_close(self):
        """CLEANUP AND CLOSE THE APP SAFELY."""
        
        self.root.quit()                      # STOP THE MAIN TKINTER LOOP
        self.root.destroy()                   # PROPERLY DESTROY THE TKINTER WINDOW
        #print("APPLICATION CLOSED CLEANLY.")  # CONFIRMATION IN THE CONSOLE
        
    def reset_plots(self):
        
        self.ax.clear()
        self.format_event_data(self.flux_df, self.energy_channel_string, self.epoch_str) 
        self.slide.set(-7.0)
        self.speed_slider.set(390)
        self.long_slider.set(0.0)
        self.long_high_slider.set(70.0)
        self.width_slider.set(40.0)
        self.create_plot()
        self.canvas.draw()
        


    # @memory_profiler.profile()
    def __call__(self):
        return 



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='GUI Program for Exploring How CME Parameters Affect the Median Profile of SEP Events')
    parser.add_argument('-ec', '--energy_channel',  type=str,   help='String defining the integral energy channel you want to look at (example 10.0--1)')
    parser.add_argument('-ff',  '--flux-file', type=str,   help='Full Filepath to the Flux File')
    parser.add_argument('-bmd',  '--benchmark', type=str, help='Full Filepath to the Benchmark Dataset File')
    args = parser.parse_args()

  
    energy_channel = args.energy_channel
    benchmark_list = args.benchmark
    flux_file = args.flux_file
    
    benchmark_list = 'GOES_integral_PRIMARY.1986-02-03.2025-09-10_sep_events 2.csv'
    flux_file = 'fluxes_GOES_integral_primary_19860101_20240905.csv'
    #print(events)
    
  
    loader(energy_channel, benchmark_list, flux_file)
   


