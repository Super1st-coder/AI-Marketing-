# open_modal = st.button("Open")
# if open_modal:
#     if not selected_rows is None and len(selected_rows) > 0 :
#         if 'current_selection' not in st.session_state:
#             st.session_state['current_selection'] = selected_rows
#         modal.open()

# modal = Modal(
#     "View Project", 
#     key="view-project",
#     padding=10,    # default value
#     max_width=800  # default value
# )

# @st.experimental_dialog("Cast your vote")
# def vote(item):
#     st.write(f"Why is {item} your favorite?")
#     reason = st.text_input("Because...")
#     if st.button("Submit"):
#         st.session_state.vote = {"item": item, "reason": reason}
#         st.rerun()

# if "vote" not in st.session_state:
#     st.write("Vote for your favorite")
#     if st.button("A"):
#         vote("A")
#     if st.button("B"):
#         vote("B")
# else:
#     f"You voted for {st.session_state.vote['item']} because {st.session_state.vote['reason']}"


# if modal.is_open():
#     with modal.container():
#         st.write("Text goes here")
#         if 'current_selection' in st.session_state:
#             current_selection = st.session_state['current_selection'] 
#             st.table(current_selection)



# else:
#     current_project = projectRepository.new(account)

# column_config = { "":  st.column_config.Column(
#             "Atributo",
#             help="Nombre del Atributo",
#             width="medium",
#             required=True,
#         ),  
#         "value": st.column_config.Column( "Valor", help="Valor del Atributo",
#             width="medium",
#             required=True  ) }
# st.data_editor(current_project,column_config=column_config)
# st.data_editor([current_project])
