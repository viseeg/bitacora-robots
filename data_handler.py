import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheet Details
SPREADSHEET_KEY = "1Sj940lQB2Ir4uHBrs-cTDftZ8dsYIoqEpxitjb9dlaA"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "google_credentials.json")

def get_excel_path():
    # Keep for compatibility with app.py sidebar text
    return "Google Sheet (Nube)"

def check_file_exists():
    # In Fase 2, we check if credentials JSON is present or defined in Streamlit secrets
    import streamlit as st
    return os.path.exists(CREDENTIALS_FILE) or "gcp_service_account" in st.secrets

def get_gspread_client():
    """
    Authenticates with Google Sheets API using the credentials JSON or Streamlit Secrets.
    """
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    import streamlit as st
    if "gcp_service_account" in st.secrets:
        # Load from Streamlit Cloud Secrets (dict format)
        creds_dict = dict(st.secrets["gcp_service_account"])
        # Normalize newlines in the private key to prevent padding / deserialization errors
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Load from local JSON file
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client

def load_sheet_as_df(client, sheet_name, skiprows=0):
    """
    Helper function to load a Google Sheet worksheet as a Pandas DataFrame,
    applying skiprows and replacing empty strings with None.
    """
    try:
        sheet = client.open_by_key(SPREADSHEET_KEY).worksheet(sheet_name)
        data = sheet.get_all_values()
    except Exception as e:
        raise Exception(f"No se pudo acceder a la hoja '{sheet_name}' en Google Sheets: {e}")
        
    if not data:
        return pd.DataFrame()
        
    # Apply skiprows
    data_skipped = data[skiprows:]
    if not data_skipped:
        return pd.DataFrame()
        
    headers = [str(h).strip() for h in data_skipped[0]]
    rows = data_skipped[1:]
    
    df = pd.DataFrame(rows, columns=headers)
    # Replace empty strings with None to preserve pandas .isna() functionality
    df = df.replace('', None)
    return df

def load_data():
    """
    Loads data from Google Sheets instead of local Excel.
    """
    if not check_file_exists():
        raise FileNotFoundError(f"Falta el archivo de credenciales 'google_credentials.json' en la carpeta del proyecto.")

    try:
        client = get_gspread_client()
    except Exception as e:
        raise Exception(f"Error al autenticar con Google Cloud. Verifica tu archivo google_credentials.json: {e}")

    # Read Inventario: Skip row 0 (title) and row 1 (flota desc)
    df_inv = load_sheet_as_df(client, 'Inventario', skiprows=2)
    # Normalize columns
    df_inv.columns = [str(c).strip() for c in df_inv.columns]
    if 'Nombre del Material' not in df_inv.columns:
        raise KeyError(f"No se encontró la columna 'Nombre del Material' en la hoja Inventario de Google Sheets. Columnas encontradas: {list(df_inv.columns)}")
        
    # Filter out empty rows or note rows
    df_inv = df_inv[df_inv['Nombre del Material'].notna()]
    df_inv = df_inv[~df_inv['Nombre del Material'].str.startswith('💡')]
    df_inv = df_inv[df_inv['Nombre del Material'].str.strip() != '']

    # Read Robots: Skip row 0 which is the title
    df_rob = load_sheet_as_df(client, 'Robots', skiprows=1)
    df_rob.columns = [str(c).strip() for c in df_rob.columns]
    df_rob = df_rob[df_rob['ID Robot'].notna()]

    # Read Registro: Skip row 0 which is the title
    df_reg = load_sheet_as_df(client, 'Registro', skiprows=1)
    df_reg.columns = [str(c).strip() for c in df_reg.columns]
    
    # Process Registro: Filter out the week title rows (e.g. "▼ Semana 01 ▼")
    df_reg_clean = df_reg[df_reg['Robot'].notna() & df_reg['Robot'].str.contains('CR.ROB', na=False)].copy()
    
    # Calculate stock dynamically in Python
    df_reg_clean['Cant_clean'] = pd.to_numeric(df_reg_clean['Cant.'], errors='coerce').fillna(0)
    used_stock = df_reg_clean.groupby('Repuesto Usado')['Cant_clean'].sum().to_dict()
    
    def calc_stock(row):
        material = str(row['Nombre del Material']).strip()
        try:
            entradas = float(row['Entradas (total)'])
        except (ValueError, TypeError):
            # Fallback to Stock Actual read from sheet
            try:
                return int(float(row['Stock Actual']))
            except:
                return 0
            
        used = used_stock.get(material, 0)
        return int(max(0, entradas - used))

    df_inv['Stock Calculado'] = df_inv.apply(calc_stock, axis=1)

    return {
        'inventario': df_inv,
        'robots': df_rob,
        'registro': df_reg,
        'registro_clean': df_reg_clean
    }

def get_robot_history(robot_id):
    """
    Returns the maintenance history of a specific robot from Google Sheets data.
    """
    data = load_data()
    df_reg = data['registro_clean']
    robot_history = df_reg[df_reg['Robot'] == robot_id].copy()
    robot_history = robot_history.sort_values(by='Semana')
    return robot_history

def get_robot_statuses():
    """
    Computes current status of each robot based on Google Sheets data.
    """
    data = load_data()
    df_rob = data['robots']
    df_reg = data['registro_clean']

    statuses = {}
    for _, r_row in df_rob.iterrows():
        r_id = r_row['ID Robot']
        r_name = r_row['Nombre del Grupo']
        r_loc = r_row['Ubicación']
        r_obs = r_row['Observaciones']
        
        state = "Sin Registro"
        last_comment = ""
        last_date = ""
        
        out_of_service = False
        if pd.notna(r_obs):
            obs_lower = str(r_obs).lower()
            if "fuera de servicio" in obs_lower or "ruedas muertas" in obs_lower:
                state = "Fuera de servicio"
                last_comment = str(r_obs)
                out_of_service = True

        r_logs = df_reg[df_reg['Robot'] == r_id]
        r_logs_active = r_logs[r_logs['Estado'].notna() & (r_logs['Estado'].str.strip() != '')]
        
        if not r_logs_active.empty and not out_of_service:
            latest_log = r_logs_active.sort_values(by='Semana').iloc[-1]
            state = latest_log['Estado']
            last_comment = latest_log['Descripción / Falla']
            last_date = latest_log['Fecha']
            
        statuses[r_id] = {
            'ID Robot': r_id,
            'Nombre del Grupo': r_name,
            'Ubicación': r_loc,
            'Estado': state,
            'Último Comentario': last_comment,
            'Fecha Último': last_date,
            'Observaciones Fijas': r_obs if pd.notna(r_obs) else ""
        }
    
    return pd.DataFrame.from_dict(statuses, orient='index')

def save_maintenance(semana, robot_id, estado, encargado, descripcion, repuesto, cantidad):
    """
    Saves a new maintenance entry directly into the Google Sheet.
    Uses batch update range B{row}:H{row} to maximize write speed.
    """
    if not check_file_exists():
        raise FileNotFoundError("No se encontró el archivo google_credentials.json.")

    client = get_gspread_client()
    sheet = client.open_by_key(SPREADSHEET_KEY).worksheet('Registro')
    
    # Fetch all values to find the row index (1-based)
    data = sheet.get_all_values()

    found_row = None
    for r_idx, row in enumerate(data, start=1):
        if len(row) >= 3:
            cell_sem = str(row[0]).strip()
            cell_rob = str(row[2]).strip()
            if cell_sem == semana and cell_rob == robot_id:
                found_row = r_idx
                break

    current_date = datetime.now().strftime("%Y-%m-%d")
    
    qty_val = int(cantidad) if cantidad and int(cantidad) > 0 else ""
    rep_val = repuesto if repuesto and repuesto != "Ninguno" else ""

    # B{row}:H{row} corresponds to columns 2 to 8
    # Col 2: Fecha, Col 3: Robot, Col 4: Estado, Col 5: Encargado, Col 6: Desc, Col 7: Repuesto, Col 8: Cant.
    row_values = [current_date, robot_id, estado, encargado, descripcion, rep_val, qty_val]

    if found_row:
        # Update columns B to H in a single request
        range_name = f"B{found_row}:H{found_row}"
        sheet.update(range_name, [row_values])
        print(f"Google Sheet: Fila {found_row} actualizada para {robot_id} en la {semana}.")
    else:
        # Append as a new row if not pre-populated in the template
        new_row = [semana, current_date, robot_id, estado, encargado, descripcion, rep_val, qty_val]
        sheet.append_row(new_row)
        print(f"Google Sheet: Nueva fila agregada para {robot_id} en la {semana}.")

    return True
