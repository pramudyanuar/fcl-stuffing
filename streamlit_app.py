import streamlit as st
import copy
from typing import List
import plotly.graph_objects as go

# ===================== MODELS =====================

class Item:
    def __init__(self, name, length, width, height, weight, quantity=1,
                 orientation_preference=None, fragile=False,
                 can_stack=True, can_stack_same_type=True,
                 item_type="box", color="#FF6B6B"):
        self.name = name
        self.item_type = item_type
        self.original_dims = (length, width, height)
        self.length = length
        self.width = width
        self.height = height
        self.weight = weight
        self.quantity = quantity
        self.orientation_preference = orientation_preference or ["lwh"]
        self.fragile = fragile
        self.can_stack = can_stack
        self.can_stack_same_type = can_stack_same_type
        self.position = None
        self.rotation = None
        self.color = color

    def get_dimensions(self, orientation):
        l, w, h = self.original_dims
        return {
            "lwh": (l, w, h),
            "lhw": (l, h, w),
            "wlh": (w, l, h),
            "whl": (w, h, l),
            "hlw": (h, l, w),
            "hwl": (h, w, l),
        }[orientation]

    def set_orientation(self, orientation):
        self.length, self.width, self.height = self.get_dimensions(orientation)
        self.rotation = orientation

    def get_volume(self):
        l, w, h = self.original_dims
        return l * w * h


class Container:
    def __init__(self, length, width, height, max_weight):
        self.length = length
        self.width = width
        self.height = height
        self.max_weight = max_weight
        self.items = []
        self.current_weight = 0

    def check_overlap(self, item, x, y, z, other):
        px, py, pz = other.position
        return not (
            x + item.length <= px or x >= px + other.length or
            y + item.width <= py or y >= py + other.width or
            z + item.height <= pz or z >= pz + other.height
        )

    def is_valid(self, item, x, y, z):
        if x + item.length > self.length: return False
        if y + item.width > self.width: return False
        if z + item.height > self.height: return False
        if self.current_weight + item.weight > self.max_weight: return False

        for other in self.items:
            if self.check_overlap(item, x, y, z, other):
                return False
        return True

    def add_item(self, item, x, y, z):
        item.position = (x, y, z)
        self.items.append(item)
        self.current_weight += item.weight


# ===================== PACKER =====================

class BinPacker:
    def __init__(self, L, W, H, max_weight):
        self.container = Container(L, W, H, max_weight)

    def generate_positions(self):
        pos = {(0,0,0)}
        for it in self.container.items:
            x,y,z = it.position
            pos.add((x+it.length, y, z))
            pos.add((x, y+it.width, z))
            pos.add((x, y, z+it.height))
        return sorted(pos, key=lambda p:(p[0], p[2], p[1]))

    def pack(self, items: List[Item]):
        expanded=[]
        for it in items:
            for i in range(it.quantity):
                new=copy.deepcopy(it)
                new.quantity=1
                new.name=f"{it.name}_{i+1}"
                expanded.append(new)

        expanded.sort(key=lambda x:(-x.weight, -x.get_volume()))

        for item in expanded:
            placed=False
            for x,y,z in self.generate_positions():
                for o in item.orientation_preference:
                    item.set_orientation(o)
                    if self.container.is_valid(item,x,y,z):
                        self.container.add_item(item,x,y,z)
                        placed=True
                        break
                if placed: break
        return self.container


# ===================== VISUALIZATION =====================

def draw_box(x, y, z, length, width, height, color, name="", show_legend=True):
    """Draw a 3D box with proper faces and edges"""
    vertices = [
        [x, x+length, x+length, x, x, x+length, x+length, x],
        [y, y, y+width, y+width, y, y, y+width, y+width],
        [z, z, z, z, z+height, z+height, z+height, z+height]
    ]
    
    # Define the 6 faces (triangles)
    i = [0, 0, 0, 1, 2, 4, 4, 6, 0, 1, 2, 4]
    j = [1, 2, 4, 2, 3, 5, 6, 7, 4, 5, 6, 5]
    k = [2, 3, 5, 3, 7, 6, 7, 3, 5, 6, 7, 7]
    
    trace = go.Mesh3d(
        x=vertices[0], y=vertices[1], z=vertices[2],
        i=i, j=j, k=k,
        color=color,
        opacity=0.8,
        name=name,
        showlegend=show_legend,
        flatshading=False
    )
    return trace

def draw_container(container: Container):
    fig = go.Figure()

    # Draw container box
    fig.add_trace(draw_box(0, 0, 0, container.length, container.width, container.height, 
                           color="rgba(200, 200, 200, 0.2)", name="Container", show_legend=False))
    
    # Draw container edges
    edges_lines = [
        # Bottom edges
        ([0, container.length], [0, 0], [0, 0]),
        ([0, 0], [0, container.width], [0, 0]),
        ([container.length, container.length], [0, container.width], [0, 0]),
        ([0, container.length], [container.width, container.width], [0, 0]),
        # Top edges
        ([0, container.length], [0, 0], [container.height, container.height]),
        ([0, 0], [0, container.width], [container.height, container.height]),
        ([container.length, container.length], [0, container.width], [container.height, container.height]),
        ([0, container.length], [container.width, container.width], [container.height, container.height]),
        # Vertical edges
        ([0, 0], [0, 0], [0, container.height]),
        ([container.length, container.length], [0, 0], [0, container.height]),
        ([0, 0], [container.width, container.width], [0, container.height]),
        ([container.length, container.length], [container.width, container.width], [0, container.height]),
    ]
    
    for ex, ey, ez in edges_lines:
        fig.add_trace(go.Scatter3d(
            x=ex, y=ey, z=ez,
            mode='lines',
            line=dict(color='black', width=3),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Draw items
    for item in container.items:
        x, y, z = item.position
        fig.add_trace(draw_box(x, y, z, item.length, item.width, item.height, 
                              color=item.color, name=item.name, show_legend=True))

    fig.update_layout(
        scene=dict(
            aspectmode='data',
            xaxis=dict(title='Length (cm)', showgrid=True, backgroundcolor="rgba(230, 230,230, 0.5)"),
            yaxis=dict(title='Width (cm)', showgrid=True, backgroundcolor="rgba(230, 230,230, 0.5)"),
            zaxis=dict(title='Height (cm)', showgrid=True, backgroundcolor="rgba(230, 230,230, 0.5)"),
            camera=dict(eye=dict(x=1.2, y=1.2, z=1))
        ),
        title="3D Container Visualization",
        showlegend=True,
        height=700,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    return fig


# ===================== STREAMLIT UI =====================

st.title("📦 FCL Container Loading Simulator")

st.sidebar.header("Container Settings")
L = st.sidebar.number_input("Length (cm)", value=590)
W = st.sidebar.number_input("Width (cm)", value=235)
H = st.sidebar.number_input("Height (cm)", value=239)
MW = st.sidebar.number_input("Max Weight (kg)", value=28000)

st.header("Items")

if "item_list" not in st.session_state:
    st.session_state.item_list=[]

# ---------- Dummy Data Button ----------
if st.button("🧪 Isi Dummy Data"):
    st.session_state.item_list = [
        Item("Box Small", 50, 40, 30, 10, quantity=5, color="#FF6B6B"),
        Item("Box Medium", 80, 60, 50, 25, quantity=3, color="#4ECDC4"),
        Item("Sack", 100, 45, 30, 45, quantity=2, color="#95E1D3"),
        Item("Big Crate", 120, 100, 90, 80, quantity=1, color="#FFA07A"),
    ]
    st.success("Dummy items loaded!")

if st.button("🗑 Clear Items"):
    st.session_state.item_list=[]

# ---------- Add Item Form ----------
with st.form("add_item"):
    c1,c2,c3=st.columns(3)
    name=c1.text_input("Name")
    length=c1.number_input("Length", value=50)
    width=c2.number_input("Width", value=40)
    height=c3.number_input("Height", value=30)
    weight=c1.number_input("Weight", value=10)
    qty=c2.number_input("Qty", value=1)
    color=c3.color_picker("Color", "#FF6B6B")

    if st.form_submit_button("Add Item"):
        st.session_state.item_list.append(Item(name,length,width,height,weight,qty,color=color))

# ---------- Show Items ----------
for it in st.session_state.item_list:
    st.write(f"📦 {it.name} | {it.quantity} pcs | {it.length}x{it.width}x{it.height} cm")

# ---------- Run Packing ----------
if st.button("🚀 Run Packing"):
    packer=BinPacker(L,W,H,MW)
    container=packer.pack(st.session_state.item_list)

    st.success(f"Packed {len(container.items)} items | Weight {container.current_weight:.1f} kg")
    st.plotly_chart(draw_container(container), use_container_width=True)