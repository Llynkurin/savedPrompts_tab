import gradio as gr
import html

from modules import ui_extra_networks_user_metadata

class PromptUserMetadataEditor(ui_extra_networks_user_metadata.UserMetadataEditor):
    def __init__(self, ui, tabname, page):
        super().__init__(ui, tabname, page)

        self.edit_notes = None
        self.edit_activation_text = None
        self.edit_negative_text = None

    def save_prompt_user_metadata(self, name, description, activation_text, negative_text, notes):

        user_metadata = self.get_user_metadata(name)       
        user_metadata["description"] = description
        user_metadata["activation text"] = activation_text
        user_metadata["negative text"] = negative_text
        user_metadata["notes"] = notes
        self.write_user_metadata(name, user_metadata)

    def put_values_into_components(self, name):
        user_metadata = self.get_user_metadata(name)        
        default_values = super().put_values_into_components(name)

        return [
            default_values[0],  
            default_values[1],  
            default_values[2],  
            default_values[3],  
            user_metadata.get('notes', ''), 
            user_metadata.get('activation text', ''), 
            user_metadata.get('negative text', ''), 
        ]

    def create_editor(self):

        self.create_default_editor_elems()
        self.edit_notes = gr.TextArea(label='Notes', lines=4)
        self.edit_activation_text = gr.TextArea(label='Activation Text (Prompt)', info="This text will be inserted into the positive prompt.", lines=4)
        self.edit_negative_text = gr.TextArea(label='Negative Text (Prompt)', info="This text will be inserted into the negative prompt.", lines=4)

        self.create_default_buttons()
        viewed_components = [
            self.edit_name,
            self.edit_description,
            self.html_filedata,
            self.html_preview,
            self.edit_notes,
            self.edit_activation_text,
            self.edit_negative_text,
        ]

        self.button_edit.click(
            fn=self.put_values_into_components,
            inputs=[self.edit_name_input], 
            outputs=viewed_components 
        ).then(
            fn=lambda: gr.update(visible=True), 
            inputs=[],
            outputs=[self.box]
        )
        edited_components = [
            self.edit_description,       
            self.edit_activation_text,   
            self.edit_negative_text,     
            self.edit_notes,             
        ]

        self.setup_save_handler(self.button_save, self.save_prompt_user_metadata, edited_components)
