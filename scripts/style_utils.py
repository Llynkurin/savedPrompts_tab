from modules import scripts
from modules import shared
import os
import shutil
import yaml
from pathlib import Path
import errno

BASE_DIR = scripts.basedir()
RES_FOLDER = os.path.join(BASE_DIR, "resources")
WILDCARDS_FOLDER = getattr(shared.opts, "wcc_wildcards_directory","").split("\n")
WILDCARDS_FOLDER = [wdir for wdir in WILDCARDS_FOLDER if os.path.isdir(wdir)]
WILD_STR = getattr(shared.opts, "dp_parser_wildcard_wrap", "__")
STRAY_RES_folder = os.path.join(BASE_DIR, "STRAY_RESOURCES")
COLL_PREV_folder = os.path.join(BASE_DIR, "COLLECTED_PREVIEWS")
_tmp_bak_ = os.path.join(BASE_DIR, "_tmp_bak_")

def find_ext_wildcard_paths():
    try:
        from modules.paths import extensions_dir, script_path
        EXT_PATH = Path(extensions_dir).absolute()
    except ImportError:
        FILE_DIR = Path().absolute()
        EXT_PATH = FILE_DIR.joinpath("extensions").absolute()
    found = list(EXT_PATH.glob("*/wildcards/"))
    try:
        from modules.shared import opts
    except ImportError:
        opts = None
    
    custom_paths = [
        getattr(shared.cmd_opts, "wildcards_dir", None),    
        getattr(opts, "wildcard_dir", None),                
    ]
    for path in [Path(p).absolute() for p in custom_paths if p is not None]:
        if path.exists():
            found.append(path)
    return [str(x) for x in found]

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def collect_Wildcards(wildcards_dirs):
    collected_paths = []
    if not wildcards_dirs:
        print("___Wildcard Directories is not setup yet!___")
    for wildcards_dir in wildcards_dirs:
        for root, dirs, files in os.walk(wildcards_dir):
            for file in files:
                if file.lower().endswith(".txt"):
                    wild_path_txt = os.path.relpath(os.path.join(root, file), wildcards_dir).replace(os.path.sep, "/").replace(".txt", "")
                    collected_paths.append(wild_path_txt)
                elif file.lower().endswith((".yaml", ".yml")):
                    collected_paths += get_yaml_paths(os.path.join(root, file))
    return list(collected_paths)

def get_yaml_paths(yaml_file_path):
    def traverse(data, path=''):
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}/{key}" if path else key
                traverse(value, new_path)
        else:
            paths.add(path)
    
    try:
        with open(yaml_file_path, 'r') as file:
            data = yaml.safe_load(file)
        paths = set()
        traverse(data)
        return list(paths)
    except yaml.YAMLError as e:
        print(f"Error occured while trying to load the file {yaml_file_path} ")
        print(f"Exception arised : {e} ")
        return []

def get_safe_name(selected_wild_path, wild_paths_list, inclusion_level = 2):
    path_parts = selected_wild_path.split('/')
    if len(path_parts) > inclusion_level:
        parent = path_parts[-inclusion_level-1]
    else:
        parent = ""
    
    curated_format_sel = '/'.join(path_parts[-inclusion_level:])
    curated_format_list = ['/'.join(wild_path.split('/')[-inclusion_level:]) for wild_path in wild_paths_list]
    
    occurance_count  = curated_format_list.count(curated_format_sel)
    if occurance_count > 1 :
        count = curated_format_list.count(curated_format_sel) + 1
        suffix = parent if parent else count
        return f"{curated_format_sel}({suffix})" , parent
    else:
        return curated_format_sel , parent

def get_safe_name_2(selected_wild_path, wild_paths_list):
    path_parts = selected_wild_path.split('/')
    parent = path_parts[-2] if len(path_parts) > 1 else ""
    aux_fallback_parent = path_parts[-3] if len(path_parts) > 2 else ""
    
    curated_format_list = ['/'.join(wild_path.split('/')[-2:]) for wild_path in wild_paths_list]
    
    occurance_count = 0
    occurance_count  = curated_format_list.count('/'.join(path_parts[-1:]))
    occurance_count_aux  = curated_format_list.count('/'.join(path_parts[-2:]))
    
    if occurance_count_aux > 1 :
        suffix = f"{aux_fallback_parent}/{parent}" if aux_fallback_parent else f"{parent}({occurance_count_aux+1})"
        return f"{path_parts[-1]}({suffix})" , parent
    else:
        occurance_count_str = "" if occurance_count == 0 else f"({occurance_count+1})"
        suffix = parent if parent else occurance_count_str
        return f"{path_parts[-1]}({suffix})" , parent

def enforce_asset_rules(active_wildcards, scan_dir):
    print("PromptTab: Enforcing strict asset rules...")
    if not os.path.isdir(scan_dir):
        return 0

    VALID_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    active_wildcards_set = {w.upper() for w in active_wildcards}
    archived_files_count = 0

    def archive_file(file_path, reason):
        nonlocal archived_files_count
        try:
            relative_file_path = os.path.relpath(file_path, scan_dir)
            relative_dir = os.path.relpath(scan_dir, BASE_DIR)
            archive_dest_path = os.path.join(_tmp_bak_, relative_dir, relative_file_path)
            
            os.makedirs(os.path.dirname(archive_dest_path), exist_ok=True)
            shutil.move(file_path, archive_dest_path)
            archived_files_count += 1
        except Exception as e:
            print(f"Error archiving {reason} file {file_path}: {e}")

    for root, dirs, files in os.walk(scan_dir):
        if os.path.abspath(root).startswith(os.path.abspath(_tmp_bak_)):
            continue

        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)
            
            is_json = ext.lower() == '.json'
            is_image = ext.lower() in VALID_IMAGE_EXTENSIONS

            if not (is_json or is_image):
                archive_file(file_path, "non-conforming type")
                continue

            relative_file_path = os.path.relpath(file_path, scan_dir)
            base_name_candidate, _ = os.path.splitext(relative_file_path)
            
            if base_name_candidate.lower().endswith('.preview'):
                base_name = base_name_candidate[:-len('.preview')]
            else:
                base_name = base_name_candidate

            formatted_base_name = base_name.replace(os.path.sep, "/").upper()
            
            if formatted_base_name not in active_wildcards_set:
                archive_file(file_path, "stale")

    if archived_files_count > 0:
        print(f"PromptTab: Archived {archived_files_count} non-conforming or stale asset(s).")

    for root, dirs, files in os.walk(scan_dir, topdown=False):
        if not os.path.isdir(root) or os.path.abspath(root).startswith(os.path.abspath(_tmp_bak_)):
            continue
        if not os.listdir(root):
            try:
                os.rmdir(root)
            except OSError as e:
                print(f"Error removing empty directory {root}: {e}")
    
    return archived_files_count

if(not WILDCARDS_FOLDER): WILDCARDS_FOLDER = find_ext_wildcard_paths()
