"""Best-effort metadata-driven ComfyUI editable workflow export.

ComfyUI's API prompt format and UI workflow format are different. We use
/object_info to create typed edges and widgets, and never claim GUI import PASS.
"""
from __future__ import annotations
from typing import Any


def _link(x: Any) -> bool:
    return (isinstance(x,list) and len(x)==2 and isinstance(x[0],str)
            and type(x[1]) is int)


def ui_graph(graph:dict[str,Any], info:dict[str,Any]) -> dict[str,Any]:
    data_nodes=[]
    edges=[]
    byid={}
    for ni,(nid,node) in enumerate(graph.items()):
        cls=node['class_type']
        meta=info[cls]
        cfg=meta.get('input',{})
        order=meta.get('input_order',{})
        ordered=[]
        for group in ('required','optional','hidden'):
            for key in order.get(group, list(cfg.get(group,{}))):
                if key in node['inputs'] and key not in ordered:
                    ordered.append(key)
        ordered.extend(key for key in node['inputs'] if key not in ordered)
        inputs=[]
        widgets=[]
        for name in ordered:
            value=node['inputs'][name]
            if _link(value):
                src,ix=value
                sm=info[graph[src]['class_type']]
                outputs=sm.get('output',[])
                if ix >= len(outputs):
                    raise ValueError(f'INVALID_OUTPUT_SLOT: {src}[{ix}]')
                typ=outputs[ix] if isinstance(outputs[ix],str) else '*'
                eid=len(edges)+1
                edges.append([eid,int(src),ix,int(nid),len(inputs),typ])
                inputs.append({'name':name,'type':typ,'link':eid})
            else:
                widgets.append(value)
        out_types=meta.get('output',[])
        out_names=meta.get('output_name') or []
        out=[]
        for ix,typ in enumerate(out_types):
            out.append({'name':out_names[ix] if ix<len(out_names) else f'output_{ix}',
                        'type':typ if isinstance(typ,str) else '*',
                        'links':None,'slot_index':ix})
        # Independent node columns: first 4 input/loading, 5-9 conditioning,
        # 10+ sampling/output. Layout is advisory only.
        col = 0 if ni<4 else (1 if ni<9 else 2)
        row = ni if ni<4 else (ni-4 if ni<9 else ni-9)
        datum={'id':int(nid),'type':cls,'pos':[col*520,row*280],
               'size':[380,210],'flags':{},'order':ni,'mode':0,
               'inputs':inputs,'outputs':out,
               'properties':{'Node name for S&R':cls},'widgets_values':widgets}
        data_nodes.append(datum)
        byid[int(nid)]=datum
    for edge in edges:
        eid,src,slot,_,_,_=edge
        cur=byid[src]['outputs'][slot]
        if cur['links'] is None:cur['links']=[]
        cur['links'].append(eid)
    return {'last_node_id':max(int(k) for k in graph),
            'last_link_id':len(edges),'nodes':data_nodes,
            'links':edges,'groups':[],'config':{},'extra':{},'version':0.4}
