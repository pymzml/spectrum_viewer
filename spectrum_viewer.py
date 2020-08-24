#!/usr/bin/env python3

import sys
import os

import pymzml

import plotly.graph_objs as go

import dash
import dash_core_components as dcc
import dash_html_components as html

ACCESSIONS_INFO=[
    ("MS:1000130", "positive scan"),
    ("MS:1000128", "profile spectrum"),
    ("MS:1000504", "base peak m/z"),
    ("MS:1000505", "base peak intensity" ),
    ("MS:1000285", "total ion current" ),
    ("MS:1000528", "lowest observed m/z" ),
    ("MS:1000527", "highest observed m/z" ),
    # ("MS:1000796", "spectrum title" ),
    ("MS:1000512", "filter string" ),
    ("MS:1000616", "preset scan configuration" ),
    ("MS:1000927", "ion injection time" ),
    ("MS:1000501", "scan window lower limit"),
    ("MS:1000500", "scan window upper limit"),
    ("MS:1001581", "FAIMS compensation voltage")
]

print('loading run...')
run = pymzml.run.Reader(sys.argv[1])

all_ids = []
for spec_id, offset in run.info['offset_dict'].items():
    try:
        all_ids.append(int(spec_id))
    except:
        continue
FIRST_SPECTRUM_ID = min(all_ids)
LAST_SPECTRUM_ID = max(all_ids)

p = pymzml.plot.Factory()
p.new_plot()

tic_x=[]
tic_y=[]
for x,y in run['TIC'].peaks():
    tic_x.append(x)
    tic_y.append(y)
max_tic = max(tic_y)

tic_annotation = []

for spec_id, RT in zip(all_ids, tic_x):
    tic_annotation.append(
        'RT: {0:1.3f}<br>ID: {1}'.format(
            RT,
            spec_id
        )
    )

app = dash.Dash(__name__)

app.layout = html.Div([
    dcc.Graph(
        id='spectrum-plot',
        style={
            'fontFamily': 'Helvetica',
        }
    ),
    html.H3(
        children='Please specify spectrum ID',
        style={
            'fontFamily': 'Helvetica',
        }
    ),
    dcc.Input(
        id='spectrum-input-field',
        value=FIRST_SPECTRUM_ID,
        type='text',
        style={
            'width': '20%',
            'height': '30px',
            'lineHeight': '30px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'fontFamily': 'Helvetica',
            'fontSize': '130%'
        }
    ),
    html.Button(id="prev-button", n_clicks=0, children="Previous spectrum"),
    html.Button(id="next-button", n_clicks=0, children="Next spectrum"),
    dcc.Graph(
        id='tic-plot',
    ),
])





def get_spectrum(spectrum_id):
    return run[spectrum_id]

def sanitize_id(spectrum_id_from_input):
    if spectrum_id_from_input not in [None, '']:
        spectrum_id  = int(spectrum_id_from_input)
    else:
        spectrum_id = FIRST_SPECTRUM_ID
    if spectrum_id < FIRST_SPECTRUM_ID:
        spectrum_id = FIRST_SPECTRUM_ID
    if spectrum_id > LAST_SPECTRUM_ID:
        spectrum_id = LAST_SPECTRUM_ID
    return spectrum_id


@app.callback(
    dash.dependencies.Output('tic-plot', 'figure'),
    [
        dash.dependencies.Input('spectrum-input-field', 'value'),
        dash.dependencies.Input("next-button", "n_clicks"),
        dash.dependencies.Input("prev-button", "n_clicks")
    ]
)
def update_TIC( spectrum_id_from_input=None, next_n_clicks=0, prev_n_clicks=0):
    spectrum_id = sanitize_id(spectrum_id_from_input)
    spectrum_id = update_spectrum_id(spectrum_id, next_n_clicks, prev_n_clicks) 
    spectrum = get_spectrum(spectrum_id)
    rt = spectrum.scan_time[0]
    figure = {
        'data':[
            {
                'x':tic_x,
                'y':tic_y,
                'line':{'color':'black'},
                'text':tic_annotation
            },
            {
                'x':[rt, rt],
                'y':[0,max_tic],
                'line':{'color':'red', 'width':2}, 
                'text':[
                    '',
                    'RT: {0}<br>ID: {1}'.format(
                        rt,
                        spectrum_id
                    )
                ]
            }
        ],
        'layout':go.Layout(
            xaxis={ 'title': 'RT', 'autorange':False, 'range':[0,max(tic_x)]},
            yaxis={'title': 'Intensity',},
            margin={'l': 40, 'b': 40, 't': 40, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest',
            showlegend=False,
            title = 'TIC'
        )
    }
    return figure


@app.callback(
    [
        dash.dependencies.Output('next-button','n_clicks'),
        dash.dependencies.Output('prev-button','n_clicks'),
    ],
    [
        dash.dependencies.Input('spectrum-input-field', 'value')
    ]
 )
def update(reset):
    return 0, 0



@app.callback(
    dash.dependencies.Output('spectrum-plot', 'figure'),
    [
        dash.dependencies.Input('spectrum-input-field', 'value'),
        dash.dependencies.Input("next-button", "n_clicks"),
        dash.dependencies.Input("prev-button", "n_clicks")
    ]
)
def trigger_new_spec_from_input( spectrum_id_from_input=None, next_n_clicks=0, prev_n_clicks=0):
    spectrum_id = sanitize_id(spectrum_id_from_input)
    spectrum_id = update_spectrum_id(spectrum_id, next_n_clicks, prev_n_clicks)
    spectrum = get_spectrum(spectrum_id)
    return update_figure(spectrum)



def update_spectrum_id(spectrum_id, next_n_clicks, prev_n_clicks):
    total_shift = next_n_clicks-prev_n_clicks
    spectrum_id += total_shift
    if spectrum_id < 1:
        spectrum_id = 1
    return spectrum_id

def update_figure(spectrum):
    peak_list=spectrum.peaks('centroided')
    # if len(peak_list) ==0:
    #     peak_list=[(0,0)]
    spectrum_plot = p.add(
        peak_list,
        color = ( 0, 0, 0 ),
        style = 'sticks',
        name = 'peaks'
    )
    new_spectrum_plot={}
    new_spectrum_plot['x'] = spectrum_plot['x'] 
    new_spectrum_plot['y'] = spectrum_plot['y']
    new_spectrum_plot['line']={'color':'black'}
    # print(spectrum_plot)
    title = 'MS{0} Spectrum {1} @ RT: {2:1.3f} [{3}s] of run {4}'.format(
        spectrum.ms_level,
        spectrum.ID,
        spectrum.scan_time[0],
        spectrum.scan_time[1],
        os.path.basename(sys.argv[1])
    )
    if spectrum.ms_level == 2:
        tmp_selected_precursors = spectrum.selected_precursors[0]
        format_str_template = '<br>'
        for key, format_template in [ ('mz',' Precursor m/z: {0}'), ('i', '; intensity {0:1.2e}'), ('charge','; charge: {0}') ]:
            if key in tmp_selected_precursors.keys():
                format_str_template += format_template.format(tmp_selected_precursors[key])
        title += format_str_template
    info_text='spectrum info'
    for ms_acc, acc_name in ACCESSIONS_INFO:
        acc_value = spectrum.get(ms_acc,None)
        if acc_value is not None:
            info_text +='<br>{0}: {1}'.format(acc_name, acc_value)
    max_x = max([x for x in new_spectrum_plot['x'] if x is not None])
    max_y = max([y for y in new_spectrum_plot['y'] if y is not None])
    info_plot=go.Scatter(
        x=[max_x-5],
        y=[max_y+max_y/20],
        text=[info_text],
        mode='markers',
        marker={'color':'black'},
        hoverinfo='text'
    )
    return {
        'data': [new_spectrum_plot, info_plot],
        'layout': go.Layout(
            xaxis={ 'title': 'm/z'},
            yaxis={'title': 'Intensity',},
            margin={'l': 40, 'b': 40, 't': 80, 'r': 10},
            legend={'x': 0, 'y': 1},
            hovermode='closest',
            title = title,
            showlegend=False,
            annotations=[
                {
                    "x": max_x-5,
                    "y":max_y+max_y/20,
                    "xref": "x",
                    "yref": "y",
                    "text": 'info',
                    "textangle": 0,
                    "font": {"size": 10, "color": 'black'},
                    "align": "center",
                    "showarrow": False,
                    "xanchor": "center",
                    "yanchor": "bottom",
                    # 'textposition': 'top'
                }
            ]
        )
    }


if __name__ == '__main__':
    app.run_server(debug=True)
