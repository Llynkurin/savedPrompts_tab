import os
import glob
import json
import gradio as gr
from collections import Counter 
from modules import scripts, shared, ui_extra_networks, script_callbacks
from modules.ui_extra_networks import quote_js
from scripts.ui_edit_prompt_metadata import PromptUserMetadataEditor
try:
    from scripts.style_utils import collect_Wildcards, WILDCARDS_FOLDER, WILD_STR, enforce_asset_rules
except ImportError:
    print("PromptTab: Could not import from style_utils.py. Please ensure the file is in the extension's scripts folder.")
    collect_Wildcards = lambda x: []
    WILDCARDS_FOLDER = []
    WILD_STR = "__"
    enforce_asset_rules = lambda x, y: None

PROMPTS_DIR = os.path.join(scripts.basedir(), "Prompts")

def prompt_tab_cleanup_callback():
    print("PromptTab: Cleanup action triggered from settings page.")
    wildcard_paths = collect_Wildcards(WILDCARDS_FOLDER)
    archived_count = enforce_asset_rules(wildcard_paths, PROMPTS_DIR)
    
    if archived_count > 0:
        status_message = f"Cleanup Ran: Archived {archived_count} files. Refresh page to run again."
    else:
        status_message = "Cleanup Ran: No stale files found. Refresh page to run again."
    
    return gr.Button.update(value=status_message)

def on_ui_settings():
    section = ("saved_prompts", "Saved Prompts")
    shared.opts.add_option(
        key="prompt_tab_action_clean_stale",
        info=shared.OptionInfo(
            "Clean Stale Assets",
            "Moves prompt assets (previews, metadata) that don't correspond to an active wildcard to a backup folder (_tmp_bak_). Action runs when settings page is loaded.",
            gr.Button,
            component_args={},
            refresh=prompt_tab_cleanup_callback,
            section=section
        )
    )

class ExtraNetworksPageSavedPrompts(ui_extra_networks.ExtraNetworksPage):
    def __init__(self):
        super().__init__('Saved Prompts')
        os.makedirs(PROMPTS_DIR, exist_ok=True)
        
        self.prompt_metadata_cache = {}
        self.prompt_name_cache = {}
        
    def ensure_prompt_json_exists(self, wildcard_path):
        json_path = os.path.join(PROMPTS_DIR, wildcard_path.replace('/', os.path.sep) + '.json')
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        if not os.path.exists(json_path):
            activation_text = f"{WILD_STR}{wildcard_path}{WILD_STR}"
            default_metadata = {
                "description": "", "activation text": activation_text,
                "negative text": "", "notes": ""
            }
            try:
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(default_metadata, f, indent=4)
                return default_metadata 
            except Exception as e:
                print(f"Error creating prompt JSON for '{wildcard_path}': {e}")
        return None 
    
    def precompute_prompt_names(self, wildcard_paths):
        name_cache = {}
        base_name_counts = Counter(path.split('/')[-1] for path in wildcard_paths)
        
        for path in wildcard_paths:
            parts = path.split('/')
            base_name = parts[-1]
            category = parts[-2] if len(parts) > 1 else ""
            
            if base_name_counts[base_name] > 1:
                display_name = f"{base_name} ({category})"
            else:
                display_name = base_name
            name_cache[path] = (display_name, category)
        return name_cache
    
    def refresh(self):
        wildcard_paths = collect_Wildcards(WILDCARDS_FOLDER)
        self.prompt_name_cache = self.precompute_prompt_names(wildcard_paths)
        temp_metadata_cache = {}
        
        for path in wildcard_paths:
            self.ensure_prompt_json_exists(path)
        
        all_json_files = glob.glob(os.path.join(PROMPTS_DIR, '**/*.json'), recursive=True)
        for json_path in all_json_files:
            wildcard_path = os.path.splitext(os.path.relpath(json_path, PROMPTS_DIR).replace(os.path.sep, '/'))[0]
            
            if wildcard_path in self.prompt_name_cache:
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        temp_metadata_cache[wildcard_path] = json.load(f)
                except Exception as e:
                    print(f"Error loading prompt JSON for '{wildcard_path}': {e}")
                    temp_metadata_cache[wildcard_path] = {}
        self.prompt_metadata_cache = temp_metadata_cache
        
    def create_item(self, name, user_metadata, **kwargs):
        display_name, category = self.prompt_name_cache.get(name, (name.split('/')[-1], ''))
        json_filename = os.path.join(PROMPTS_DIR, name.replace('/', os.path.sep) + '.json')
        base_path = os.path.splitext(json_filename)[0]
        
        item = {
            "name": display_name, "filename": json_filename,
            "shorthash": str(hash(json_filename))[-10:], "preview": self.find_preview(base_path),
            "description": user_metadata.get("description", ""),
            "search_terms": [self.search_terms_from_path(json_filename)], "prompt": "",
            "negative_prompt": "", "local_preview": f"{base_path}.{shared.opts.samples_format}",
            "metadata": None, "user_metadata": user_metadata, 
            "sort_keys": {'default': f"{category.lower()}-{display_name.lower()}", 'name': display_name.lower()},
        }
        
        activation_text = user_metadata.get("activation text", f"{WILD_STR}{name}{WILD_STR}")
        negative_text = user_metadata.get("negative text", "")
        item["prompt"] = quote_js(activation_text)
        item["negative_prompt"] = quote_js(negative_text)
        return item
        
    def list_items(self):
        self.refresh()
        sorted_items = sorted(self.prompt_metadata_cache.items(), key=lambda x: x[0].lower())
        
        for name, user_metadata in sorted_items:
            yield self.create_item(name, user_metadata)
        
    def allowed_directories_for_previews(self):
        return [PROMPTS_DIR]
        
    def create_user_metadata_editor(self, ui, tabname):
        return PromptUserMetadataEditor(ui, tabname, self)

def on_before_ui():
    ui_extra_networks.register_page(ExtraNetworksPageSavedPrompts())

script_callbacks.on_before_ui(on_before_ui)
script_callbacks.on_ui_settings(on_ui_settings)
