import os
import time

import threading
import demo_util
import streamlit as st
from demo_util import DemoFileIOHelper, DemoTextProcessingHelper, DemoUIHelper, truncate_filename
import logging  # 确保已导入logging


def handle_not_started():
    if st.session_state["page3_write_article_state"] == "not started":
        _, search_form_column, _ = st.columns([2, 5, 2])
        with search_form_column:
            with st.form(key='search_form'):
                # Text input for the search topic
                DemoUIHelper.st_markdown_adjust_size(content="Enter the topic you want to learn in depth:",
                                                     font_size=18)
                st.session_state["page3_topic"] = st.text_input(label='page3_topic', 
                                                    autocomplete="off",  # Set to a valid value or "off"
                                                    label_visibility="collapsed")
                pass_appropriateness_check = True
                # Submit button for the form
                submit_button = st.form_submit_button(label='Research')
                logging.info(f'line 25: submit_button={submit_button}, session_state={st.session_state}')
                # only start new search when button is clicked, not started, or already finished previous one
                if not submit_button and st.session_state["page3_write_article_state"] in ["not started", "show results"]:
                    logging.info(f'line 27: topic={st.session_state["page3_topic"].strip()}')
                    if not st.session_state["page3_topic"].strip():
                        logging.info(f'line 28: session_state={st.session_state}')
                        
                        pass_appropriateness_check = False
                        st.session_state["page3_warning_message"] = "topic could not be empty"

                    st.session_state["page3_topic_name_cleaned"] = st.session_state["page3_topic"].replace(
                        ' ', '_').replace('/', '_')
                    st.session_state["page3_topic_name_truncated"] = truncate_filename(st.session_state["page3_topic_name_cleaned"])
                    if not pass_appropriateness_check:
                        st.session_state["page3_write_article_state"] = "not started"
                        alert = st.warning(st.session_state["page3_warning_message"], icon="⚠️")
                        time.sleep(5)
                        alert.empty()
                    else:
                        st.session_state["page3_write_article_state"] = "initiated"


def handle_initiated():
    if st.session_state["page3_write_article_state"] == "initiated":
        current_working_dir = os.path.join(demo_util.get_demo_dir(), "DEMO_WORKING_DIR")
        if not os.path.exists(current_working_dir):
            os.makedirs(current_working_dir)

        if "runner" not in st.session_state:
            # demo_util.set_storm_runner()
            demo_util.set_costorm_runner()
        st.session_state["page3_current_working_dir"] = current_working_dir
        st.session_state["page3_write_article_state"] = "pre_writing"

def handle_pre_writing():
    if st.session_state["page3_write_article_state"] == "pre_writing":
        status_placeholder = st.empty()
        conversation_placeholder = st.empty()
        st_callback_handler = demo_util.StreamlitCallbackHandler(status_placeholder, conversation_placeholder)

        if "conversation_log" not in st.session_state:
            st.session_state["conversation_log"] = []
            runner = st.session_state["runner"]
            runner.warm_start()
            conv_turn = runner.step()
            st.session_state["conversation_log"].append(conv_turn)
            conversation_placeholder.markdown(f"**{conv_turn.role.capitalize()}**: {conv_turn.utterance}\n")
            st.session_state["page3_write_article_state"] = "awaiting_user_input"

def handle_pre_writing_threading():
    if st.session_state["page3_write_article_state"] == "pre_writing":
        status_placeholder = st.empty()
        status_placeholder.markdown("I am **Co-STORM**ing now to research the topic. (This may take 2-3 minutes.)")
        conversation_placeholder = st.empty()
        st_callback_handler = demo_util.StreamlitCallbackHandler(status_placeholder, conversation_placeholder)

        # Start the Co-STORM process in a separate thread to allow user interaction
        if "conversation_log" not in st.session_state:
            st.session_state["conversation_log"] = []
            st.session_state["lock"] = threading.Lock()

            def run_costorm():
                logging.info("Line 109:",st.session_state)
                with st.session_state["lock"]:
                    runner = st.session_state["runner"]
                    runner.warm_start()
                    for _ in range(1):  # Initial observation step
                        conv_turn = runner.step()
                        st.session_state["conversation_log"].append(conv_turn)
                        status_placeholder.markdown(f"**{conv_turn.role.capitalize()}**: {conv_turn.utterance}\n")
                st.session_state["page3_write_article_state"] = "awaiting_user_input"

            thread = threading.Thread(target=run_costorm)
            thread.start()

        st.session_state["page3_write_article_state"] = "awaiting_user_input"


def handle_awaiting_user_input():
    if st.session_state["page3_write_article_state"] == "awaiting_user_input":
        # Display conversation log in a scrollable container
        with st.container():
            st.markdown("### Conversation")
            if "conversation_log" not in st.session_state:
                st.session_state["conversation_log"] = []
            for conv_turn in st.session_state["conversation_log"]:
                role = conv_turn.role
                utterance = conv_turn.utterance
                if role.lower() == "user":
                    st.markdown(f"**You**: {utterance}")
                else:
                    st.markdown(f"**{role.capitalize()}**: {utterance}")

        # Input form at the bottom
        st.markdown("---")  # 分隔线
        with st.form(key='user_input_form', clear_on_submit=False):
            user_utterance = st.text_input(label='Your Input', placeholder='Enter your message here...')
            submit_button = st.form_submit_button(label='Send')

            if submit_button and user_utterance.strip():
                # Process user input
                st.session_state["conversation_log"].append({"role": "user", "utterance": user_utterance})
                logging.info(f"User: {user_utterance}")

                # Pass user input to Co-STORM runner
                runner = st.session_state["runner"]
                runner.step(user_utterance=user_utterance)

                # Get Co-STORM response
                conv_turn = runner.step()
                st.session_state["conversation_log"].append(conv_turn)
                logging.info(f"{conv_turn['role']}: {conv_turn['utterance']}")

                # Update conversation log display by rerunning
                if runner.knowledge_base.is_reorganized and runner.is_generation_complete():
                    st.session_state["page3_write_article_state"] = "final_writing"


def handle_final_writing():
    if st.session_state["page3_write_article_state"] == "final_writing":
        status_placeholder = st.empty()
        status_placeholder.markdown("Now generating the final article. (This may take 4-5 minutes.)")
        with st.spinner("Generating final article..."):
            # Generate report using Co-STORM
            runner = st.session_state["runner"]
            runner.knowledge_base.reorganize()
            article = runner.generate_report()

            # Save results
            output_dir = st.session_state["current_working_dir"]
            os.makedirs(output_dir, exist_ok=True)

            # Save article
            report_path = os.path.join(output_dir, "report.md")
            with open(report_path, "w") as f:
                f.write(article)
            st.session_state["final_article"] = article

            # Save instance dump
            instance_copy = runner.to_dict()
            with open(os.path.join(output_dir, "instance_dump.json"), "w") as f:
                json.dump(instance_copy, f, indent=2)

            # Save logging
            log_dump = runner.dump_logging_and_reset()
            with open(os.path.join(output_dir, "log.json"), "w") as f:
                json.dump(log_dump, f, indent=2)

            st.session_state["page3_write_article_state"] = "prepare_to_show_result"
            status_placeholder.markdown("**Final article generation complete!**")

def handle_prepare_to_show_result():
    if st.session_state["page3_write_article_state"] == "prepare_to_show_result":
        _, show_result_col, _ = st.columns([4, 3, 4])
        with show_result_col:
            if st.button("show final article"):
                st.session_state["page3_write_article_state"] = "completed"
                st.rerun()

# def handle_completed():
    
#     if st.session_state["page3_write_article_state"] == "completed":
#         # display polished article
#         current_working_dir_paths = DemoFileIOHelper.read_structure_to_dict(
#             st.session_state["page3_current_working_dir"])
#         current_article_file_path_dict = current_working_dir_paths[st.session_state["page3_topic_name_truncated"]]
#         demo_util.display_article_page(selected_article_name=st.session_state["page3_topic_name_cleaned"],
#                                        selected_article_file_path_dict=current_article_file_path_dict,
#                                        show_title=True, show_main_article=True)


def handle_completed():
    if st.session_state["page3_write_article_state"] == "completed":
        st.markdown("### Final Article")
        st.markdown(st.session_state.get("final_article", "No article generated."))

        # Download conversation log
        if st.session_state.get("conversation_log"):
            conversation_json = json.dumps(st.session_state["conversation_log"], indent=2)
            st.download_button(
                label="Download Conversation Log",
                data=conversation_json,
                file_name="conversation_log.json",
                mime="application/json"
            )

def create_new_article_page():
    demo_util.clear_other_page_session_state(page_index=3)

    if "page3_write_article_state" not in st.session_state:
        st.session_state["page3_write_article_state"] = "not started"
        logging.info('page3_write_article_state here!',st.session_state)

    handle_not_started()
    handle_initiated()
    # handle_pre_writing_threading()
    handle_pre_writing()
    handle_awaiting_user_input()
    handle_final_writing()
    handle_prepare_to_show_result()
    handle_completed()


# class StreamlitCallbackHandler:
#     def __init__(self, status_placeholder):
#         self.status_placeholder = status_placeholder

#     def on_step(self, message):
#         self.status_placeholder.markdown(message)

#     def on_complete(self):
#         self.status_placeholder.markdown("**Co-STORM** has completed its tasks.")