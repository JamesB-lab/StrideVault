import streamlit as st
import zipfile
import json
import pandas as pd
from datetime import datetime
import os
import glob
import shutil

# === helper functions ===
def msToDuration(ms):
    seconds = ms / 1000.0
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f'{hours:02.0f}:{minutes:02.0f}:{seconds:05.2f}'

def cmToMiles(x):
    return x / 100.0 / 1000.0 / 1.60934

def flatten_json(y):
    out = {}
    def flatten(x, name=""):
        if isinstance(x, dict):
            for a in x:
                if a in ['splitSummaries', 'splits']:
                    continue
                flatten(x[a], name + a + "_")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, name + str(i) + "_")
        else:
            key = name[:-1]
            if x is not None:
                try:
                    if 'timestamp' in key.lower() or 'starttime' in key.lower():
                        if isinstance(x, str) and x.isdigit():
                            x = int(x)
                        if isinstance(x, int) or isinstance(x, float):
                            x = datetime.fromtimestamp(x/1000.0)
                    if 'duration' in key.lower():
                        if isinstance(x, str) and x.isdigit():
                            x = int(x)
                        x = msToDuration(x)
                    if 'distance' in key.lower():
                        if isinstance(x, str) and x.isdigit():
                            x = int(x)
                        x = cmToMiles(x)
                    if 'elevation' in key.lower():
                        if isinstance(x, str) and x.isdigit():
                            x = int(x)
                        x = x * 0.0328084
                except:
                    pass
            out[key] = x
    flatten(y)
    return out

# === Streamlit App ===
st.title("StrideVault 🔒 - Garmin JSON Converter")
st.write("Welcome to StrideVault! Upload your Garmin .zip data and convert it to easy-to-use CSV files")

uploaded_zip = st.file_uploader("Upload your Garmin export ZIP", type="zip")

if uploaded_zip is not None:
    st.success(f"File '{uploaded_zip.name}' uploaded successfully!")

    if os.path.exists("stridevault_csv"):
        shutil.rmtree("stridevault_csv")

    with zipfile.ZipFile(uploaded_zip) as z:
        file_list = z.namelist()
        st.write("Files inside the zip (first 10):", file_list[:10])

        filtered_files = [f for f in file_list if f.endswith(".json")]

        if not filtered_files:
            st.warning("No JSON files found in the uploaded ZIP!")
        else:
            st.write("Filtered JSON files (first 10):", filtered_files[:10])

            selected_file = st.selectbox("Select a file to preview:", filtered_files)

            if selected_file:
                try:
                    with z.open(selected_file) as f:
                        text_data = f.read().decode("utf-8")
                        json_data = json.loads(text_data)
                        flattened = flatten_json(json_data)
                        df = pd.DataFrame([flattened])
                        st.write("Preview of selected JSON:", df.head())

                        csv_data = df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download this file as CSV",
                            data=csv_data,
                            file_name=os.path.splitext(os.path.basename(selected_file))[0] + ".csv",
                            mime="text/csv"
                        )
                except Exception as e:
                    st.error(f"Error reading {selected_file}: {e}")

            if st.button("Convert all JSONs to CSV"):
                skipped_files = []
                for json_filename in filtered_files:
                    try:
                        with z.open(json_filename) as f:
                            json_bytes = f.read()
                            text_data = json_bytes.decode('utf-8')
                            json_data = json.loads(text_data)
                            flattened = flatten_json(json_data)
                            df = pd.DataFrame([flattened])

                            relative_path = os.path.dirname(json_filename)
                            csv_folder_path = os.path.join("stridevault_csv", relative_path)
                            os.makedirs(csv_folder_path, exist_ok=True)

                            base_name = os.path.splitext(os.path.basename(json_filename))[0]
                            csv_output_path = os.path.join(csv_folder_path, base_name + ".csv")
                            df.to_csv(csv_output_path, index=False)
                    except Exception as e:
                        skipped_files.append(json_filename)

                st.success("All valid JSONs processed and saved to 'stridevault_csv'.")

                if skipped_files:
                    st.warning(f"Skipped {len(skipped_files)} files due to errors.")

                # show download buttons for all
                csv_files = glob.glob("stridevault_csv/**/*.csv", recursive=True)
                if csv_files:
                    st.write("### Download your CSVs:")
                    for file in csv_files:
                        file_display = file.replace("stridevault_csv/", "")
                        with open(file, "rb") as f:
                            st.download_button(
                                label=f"Download {file_display}",
                                data=f,
                                file_name=file_display,
                                mime="text/csv"
                            )
