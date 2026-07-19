# pylint: disable = invalid-name
import os
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage

from agents.agent import Agent


def get_missing_required_env_vars():
    required = ['GEMINI_API_KEY', 'SERPAPI_API_KEY', 'SENDGRID_API_KEY']
    return [name for name in required if not os.environ.get(name)]


def populate_envs(sender_email, receiver_email, subject):
    os.environ['FROM_EMAIL'] = sender_email
    os.environ['TO_EMAIL'] = receiver_email
    os.environ['EMAIL_SUBJECT'] = subject


def send_email(sender_email, receiver_email, subject, thread_id):
    try:
        populate_envs(sender_email, receiver_email, subject)
        config = {'configurable': {'thread_id': thread_id}}
        state = st.session_state.agent.graph.invoke(None, config=config)
        
        if os.environ.get('SENDGRID_API_KEY'):
            st.success('Email sent successfully!')
        else:
            st.info('SendGrid API key not set. Travel details formatted for email are previewed below.')
            email_msg = state['messages'][-1]
            if email_msg and email_msg.content:
                st.session_state.email_html = email_msg.content
                
        # Clear session state items except email_html
        for key in ['travel_info', 'thread_id']:
            st.session_state.pop(key, None)
    except Exception as e:
        st.error(f'Error sending email: {e}')


def initialize_agent():
    missing = get_missing_required_env_vars()
    if missing:
        st.session_state.agent_error = (
            'Please enter all three API credentials in the sidebar to activate the Yatra Sathi assistant.'
        )
        st.session_state.pop('agent', None)
        return

    st.session_state.pop('agent_error', None)
    if 'agent' not in st.session_state:
        try:
            st.session_state.agent = Agent()
        except Exception as e:
            st.session_state.agent_error = f"Error instantiating Agent: {e}"


def render_custom_css():
    st.markdown(
        '''
        <style>
        .main-title {
            font-size: 2.5em;
            color: #333;
            text-align: center;
            margin-bottom: 0.5em;
            font-weight: bold;
        }
        .sub-title {
            font-size: 1.2em;
            color: #333;
            text-align: left;
            margin-bottom: 0.5em;
        }
        .center-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        .query-box {
            width: 80%;
            max-width: 600px;
            margin-top: 0.5em;
            margin-bottom: 1em;
        }
        .query-container {
            width: 80%;
            max-width: 600px;
            margin: 0 auto;
        }
        </style>
        ''', unsafe_allow_html=True)


def render_ui():
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.markdown('<div class="main-title">✈️🌍 Yatra Sathi </div>', unsafe_allow_html=True)
    st.markdown('<div class="query-container">', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Enter your travel query and get flight and hotel information:</div>', unsafe_allow_html=True)
    user_input = st.text_area(
        'Travel Query',
        height=200,
        key='query',
        placeholder='Type your travel query here...',
    )
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.sidebar.image('images/yatra_sathi_ui.png', caption='Yatra Sathi - Your Travel Companion')
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔑 API Credentials")
    st.sidebar.info("All three API keys are mandatory to activate the travel search features:")
    
    # Pre-populate variables from environment if not present in session state
    for var in ['GEMINI_API_KEY', 'SERPAPI_API_KEY', 'SENDGRID_API_KEY']:
        if var not in st.session_state:
            st.session_state[var] = os.environ.get(var, '')
            
    gemini_key = st.sidebar.text_input("Gemini API Key", value=st.session_state.GEMINI_API_KEY, type="password", placeholder="Enter Gemini key (AIzaSy...)")
    serpapi_key = st.sidebar.text_input("SerpAPI API Key", value=st.session_state.SERPAPI_API_KEY, type="password", placeholder="Enter SerpAPI key...")
    sendgrid_key = st.sidebar.text_input("SendGrid API Key", value=st.session_state.SENDGRID_API_KEY, type="password", placeholder="Enter SendGrid key (SG....)")
    
    # Save changes programmatically
    recreate_agent = False
    if gemini_key != st.session_state.GEMINI_API_KEY:
        st.session_state.GEMINI_API_KEY = gemini_key
        os.environ['GEMINI_API_KEY'] = gemini_key
        os.environ['GOOGLE_API_KEY'] = gemini_key
        recreate_agent = True
        
    if serpapi_key != st.session_state.SERPAPI_API_KEY:
        st.session_state.SERPAPI_API_KEY = serpapi_key
        os.environ['SERPAPI_API_KEY'] = serpapi_key
        recreate_agent = True
        
    if sendgrid_key != st.session_state.SENDGRID_API_KEY:
        st.session_state.SENDGRID_API_KEY = sendgrid_key
        os.environ['SENDGRID_API_KEY'] = sendgrid_key
        recreate_agent = True
        
    if recreate_agent:
        st.session_state.pop('agent', None)
        st.session_state.pop('agent_error', None)
        st.rerun()

    return user_input


def process_query(user_input):
    if user_input:
        try:
            thread_id = str(uuid.uuid4())
            st.session_state.thread_id = thread_id

            messages = [HumanMessage(content=user_input)]
            config = {'configurable': {'thread_id': thread_id}}

            result = st.session_state.agent.graph.invoke({'messages': messages}, config=config)

            st.subheader('Travel Information')
            st.write(result['messages'][-1].content)

            st.session_state.travel_info = result['messages'][-1].content

        except Exception as e:
            st.error(f'Error: {e}')
    else:
        st.error('Please enter a travel query.')


def render_email_form():
    send_email_option = st.radio('Do you want to send this information via email?', ('No', 'Yes'))
    if send_email_option == 'Yes':
        with st.form(key='email_form'):
            sender_email = st.text_input('Sender Email')
            receiver_email = st.text_input('Receiver Email')
            subject = st.text_input('Email Subject', 'Yatra Sathi Travel Itinerary')
            submit_button = st.form_submit_button(label='Send Email')

        if submit_button:
            if sender_email and receiver_email and subject:
                send_email(sender_email, receiver_email, subject, st.session_state.thread_id)
            else:
                st.error('Please fill out all email fields.')


def main():
    st.set_page_config(page_title="Yatra Sathi - AI Travel Companion", page_icon="✈️", layout="centered")
    initialize_agent()
    render_custom_css()
    user_input = render_ui()

    if 'agent_error' in st.session_state:
        st.error(st.session_state.agent_error)
        return

    if st.button('Get Travel Information'):
        process_query(user_input)

    if 'travel_info' in st.session_state:
        render_email_form()

    if 'email_html' in st.session_state:
        st.subheader('Email Preview (HTML)')
        st.components.v1.html(st.session_state.email_html, height=500, scrolling=True)
        if st.button('Clear Preview'):
            st.session_state.pop('email_html', None)
            st.rerun()


if __name__ == '__main__':
    main()
