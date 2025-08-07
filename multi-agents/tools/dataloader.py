import os
from langchain.tools import tool
from typing import Annotated, Tuple, Dict
from loguru import logger as log
import pandas as pd

EXTENSION_LOADER = {}

def register_loader(file_extension: str):
    def decorator(func):
        EXTENSION_LOADER[file_extension.lower()] = func
        return func
    return decorator


# data loader functions
@tool(response_format='content_and_artifact')
def load_directory(
        directory_path: Annotated[str, 'The path to the directory to load'],
        file_type: str|None = None
    ) -> Tuple[str, Dict]:
    """
    Tool: load_directory
    Description: Loads all data in a given directory_path. 
                 If file_type is specified (e.g., 'csv'), only files 
                 with that extension are loaded.
    
    Parameters:
    ----------
    directory_path : str
        The path to the directory to load.

    file_type : str, optional
        The extension of the file type you want to load exclusively 
        (e.g., 'csv', 'xlsx', 'parquet'). If None or not provided, 
        attempts to load all recognized tabular files.
    
    Returns:
    -------
    Tuple[str, Dict]
        A tuple containing a message and a dictionary of data frames.
    """
    
    log.info(f"Directory: {directory_path}")
    
    import os
    import pandas as pd
    
    if directory_path is None:
        return f"No directory path was provided"
    
    dataframes = {}
    
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)
        
        if os.path.isdir(file_path):
            continue
        
        if file_type:
            if not filename.lower().endswith(f'.{file_type.lower()}'):
                continue
            
        try:
            dataframes[filename] = auto_loader(file_path).to_dict()
        except Exception as e:
            dataframes[filename] = f"Error loading file: {e}"
            
    return (
        f"Returned the following data frames: {list(dataframes.keys())}",
        dataframes
    )
        

def auto_loader(file_path: str):
    """
    Auto loads a file based on its extension.
    
    Parameters:
    ----------
    file_path : str
        The path to the file to load.
    
    Returns:
    -------
    pd.DataFrame
    """ 
    import pandas as pd
    
    try:
        file_extension = file_path.lower().split('.')[-1]
        log.info(file_extension)
        data_loader = EXTENSION_LOADER.get(file_extension)
        if data_loader:
            return data_loader(file_path)
        
        return f"Unsupported file extension: {file_extension}"
    except Exception as e:
        return f"Error loading file: {e}"


@register_loader('csv')
def load_csv(file_path: str) -> pd.DataFrame:
    """
    Tool: load_csv
    Description: Loads a CSV file into a pandas DataFrame.
    Args:
      file_path (str): Path to the CSV file.
    Returns:
      pd.DataFrame
    """
    import pandas as pd
    return pd.read_csv(file_path)


@register_loader('xlsx')
def load_excel(file_path: str, sheet_name=None) -> pd.DataFrame:
    """
    Tool: load_excel
    Description: Loads an Excel file into a pandas DataFrame.
    """
    import pandas as pd
    return pd.read_excel(file_path, sheet_name=sheet_name)


@register_loader('json')
def load_json(file_path: str) -> pd.DataFrame:
    """
    Tool: load_json
    Description: Loads a JSON file or NDJSON into a pandas DataFrame.
    """
    import pandas as pd
    # For simple JSON arrays
    return pd.read_json(file_path, orient="records", lines=False)


@register_loader('parquet')
def load_parquet(file_path: str) -> pd.DataFrame:
    """
    Tool: load_parquet
    Description: Loads a Parquet file into a pandas DataFrame.
    """
    import pandas as pd
    return pd.read_parquet(file_path)


@register_loader('pkl')
def load_pickle(file_path: str) -> pd.DataFrame:
    """
    Tool: load_pickle
    Description: Loads a Pickle file into a pandas DataFrame.
    """
    import pandas as pd
    return pd.read_pickle(file_path)