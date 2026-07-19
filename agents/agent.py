# pylint: disable = http-used,print-used,no-self-use

import datetime
import operator
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from agents.tools.flights_finder import flights_finder
from agents.tools.hotels_finder import hotels_finder

_ = load_dotenv()

if 'GEMINI_API_KEY' in os.environ and 'GOOGLE_API_KEY' not in os.environ:
    os.environ['GOOGLE_API_KEY'] = os.environ['GEMINI_API_KEY']

CURRENT_YEAR = datetime.datetime.now().year


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


TOOLS_SYSTEM_PROMPT = f"""You are a smart travel agency assistant.
    The current year is {CURRENT_YEAR}.
    
    To look up flights or hotels, you must output a tool-call command in the following exact format:
    
    For searching flights:
    CALL_TOOL: flights_finder
    DEPARTURE: [IATA code, e.g. DEL]
    ARRIVAL: [IATA code, e.g. AMS]
    OUTBOUND_DATE: [YYYY-MM-DD]
    RETURN_DATE: [YYYY-MM-DD]
    
    For searching hotels:
    CALL_TOOL: hotels_finder
    LOCATION: [City or Location Name]
    CHECK_IN: [YYYY-MM-DD]
    CHECK_OUT: [YYYY-MM-DD]
    
    Do not output anything else in that turn. You are allowed to make multiple tool calls in sequence.
    And in the next turn, when you receive the search results, you can make another tool call, or write your final response.
    
    When you have gathered all the necessary travel details and are ready to present the final itinerary to the user, DO NOT output 'CALL_TOOL'. Just output your final travel itinerary in clean, beautiful, human-readable markdown format.
    Always include hotel website links, flight websites, ratings, flight prices, hotel rates per night, airline companies, and hotel/airline logos (if found in the tool results) in the final output. Do not present the data as raw JSON.
    """

TOOLS = [flights_finder, hotels_finder]

EMAILS_SYSTEM_PROMPT = """Your task is to convert structured markdown-like text into a valid HTML email body.

- Do not include a ```html preamble in your response.
- The output should be in proper HTML format, ready to be used as the body of an email.
Here is an example:
<example>
Input:

I want to travel to New York from Madrid from October 1-7. Find me flights and 4-star hotels.

Expected Output:

<!DOCTYPE html>
<html>
<head>
    <title>Flight and Hotel Options</title>
</head>
<body>
    <h2>Flights from Madrid to New York</h2>
    <ol>
        <li>
            <strong>American Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:25 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:25 PM<br>
            <strong>Duration:</strong> 8 hours<br>
            <strong>Aircraft:</strong> Boeing 777<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/AA.png" alt="American Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Iberia</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 12:25 PM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 2:40 PM<br>
            <strong>Duration:</strong> 8 hours 15 minutes<br>
            <strong>Aircraft:</strong> Airbus A330<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $702<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/IB.png" alt="Iberia"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
        <li>
            <strong>Delta Airlines</strong><br>
            <strong>Departure:</strong> Adolfo Suárez Madrid–Barajas Airport (MAD) at 10:00 AM<br>
            <strong>Arrival:</strong> John F. Kennedy International Airport (JFK) at 12:30 PM<br>
            <strong>Duration:</strong> 8 hours 30 minutes<br>
            <strong>Aircraft:</strong> Boeing 767<br>
            <strong>Class:</strong> Economy<br>
            <strong>Price:</strong> $738<br>
            <img src="https://www.gstatic.com/flights/airline_logos/70px/DL.png" alt="Delta Airlines"><br>
            <a href="https://www.google.com/flights">Book on Google Flights</a>
        </li>
    </ol>

    <h2>4-Star Hotels in New York</h2>
    <ol>
        <li>
            <strong>NobleDen Hotel</strong><br>
            <strong>Description:</strong> Modern, polished hotel offering sleek rooms, some with city-view balconies, plus free Wi-Fi.<br>
            <strong>Location:</strong> Near Washington Square Park, Grand St, and JFK Airport.<br>
            <strong>Rate per Night:</strong> $537<br>
            <strong>Total Rate:</strong> $3,223<br>
            <strong>Rating:</strong> 4.8/5 (656 reviews)<br>
            <strong>Amenities:</strong> Free Wi-Fi, Parking, Air conditioning, Restaurant, Accessible, Business centre, Child-friendly, Smoke-free property<br>
            <img src="https://lh5.googleusercontent.com/p/AF1QipNDUrPJwBhc9ysDhc8LA822H1ZzapAVa-WDJ2d6=s287-w287-h192-n-k-no-v1" alt="NobleDen Hotel"><br>
            <a href="http://www.nobleden.com/">Visit Website</a>
        </li>
        <!-- More hotel entries here -->
    </ol>
</body>
</html>

</example>


"""


class Agent:

    def __init__(self):
        self._tools = {t.name: t for t in TOOLS}
        self._tools_llm = ChatGoogleGenerativeAI(model='gemini-3.5-flash')

        builder = StateGraph(AgentState)
        builder.add_node('call_tools_llm', self.call_tools_llm)
        builder.add_node('invoke_tools', self.invoke_tools)
        builder.add_node('email_sender', self.email_sender)
        builder.set_entry_point('call_tools_llm')

        builder.add_conditional_edges('call_tools_llm', Agent.exists_action, {'more_tools': 'invoke_tools', 'email_sender': 'email_sender'})
        builder.add_edge('invoke_tools', 'call_tools_llm')
        builder.add_edge('email_sender', END)
        memory = MemorySaver()
        self.graph = builder.compile(checkpointer=memory, interrupt_before=['email_sender'])

        print(self.graph.get_graph().draw_mermaid())

    @staticmethod
    def exists_action(state: AgentState):
        last_message = state['messages'][-1]
        content = getattr(last_message, 'content', '')
        if "CALL_TOOL: flights_finder" in content or "CALL_TOOL: hotels_finder" in content:
            return 'more_tools'
        return 'email_sender'

    def email_sender(self, state: AgentState):
        print('Sending email')
        email_llm = ChatGoogleGenerativeAI(model='gemini-3.5-flash', temperature=0.1)  # Instantiate another LLM
        email_message = [SystemMessage(content=EMAILS_SYSTEM_PROMPT), HumanMessage(content=state['messages'][-1].content)]
        email_response = email_llm.invoke(email_message)
        print('Email content:', email_response.content)

        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if sendgrid_api_key:
            try:
                message = Mail(from_email=os.environ['FROM_EMAIL'], to_emails=os.environ['TO_EMAIL'], subject=os.environ['EMAIL_SUBJECT'],
                               html_content=email_response.content)
                sg = SendGridAPIClient(sendgrid_api_key)
                response = sg.send(message)
                print(response.status_code)
                print(response.body)
                print(response.headers)
            except Exception as e:
                print(f"Error sending email: {e}")
        else:
            print("SENDGRID_API_KEY is not set. Skipping email dispatch, content will be previewed locally.")

        # Return the generated email content so it can be extracted and previewed in Streamlit
        return {'messages': [AIMessage(content=email_response.content, name='email_sender')]}

    def call_tools_llm(self, state: AgentState):
        messages = state['messages']
        messages = [SystemMessage(content=TOOLS_SYSTEM_PROMPT)] + messages
        message = self._tools_llm.invoke(messages)
        return {'messages': [message]}

    def invoke_tools(self, state: AgentState):
        last_message = state['messages'][-1]
        content = getattr(last_message, 'content', '')
        
        # Parse key-value parameters from the content lines
        params = {}
        for line in content.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                params[key.strip().upper()] = val.strip()
                
        tool_name = ""
        if "CALL_TOOL" in params:
            tool_name = params["CALL_TOOL"]
            
        print(f"Agent requested tool: {tool_name}")
        result = ""
        
        if tool_name == "flights_finder":
            departure = params.get("DEPARTURE")
            arrival = params.get("ARRIVAL")
            outbound = params.get("OUTBOUND_DATE")
            ret_date = params.get("RETURN_DATE")
            
            print(f"Running flights search: {departure} -> {arrival} ({outbound} to {ret_date})")
            from agents.tools.flights_finder import FlightsInput
            args = FlightsInput(
                departure_airport=departure,
                arrival_airport=arrival,
                outbound_date=outbound,
                return_date=ret_date
            )
            result = self._tools['flights_finder'].invoke({"params": args})
            
        elif tool_name == "hotels_finder":
            location = params.get("LOCATION")
            check_in = params.get("CHECK_IN")
            check_out = params.get("CHECK_OUT")
            
            print(f"Running hotels search: {location} ({check_in} to {check_out})")
            from agents.tools.hotels_finder import HotelsInput
            args = HotelsInput(
                q=location,
                check_in_date=check_in,
                check_out_date=check_out
            )
            result = self._tools['hotels_finder'].invoke({"params": args})
        else:
            result = f"Error: Unknown tool '{tool_name}' or invalid parameters."
            
        tool_response = f"Search Results from {tool_name}:\n\n{result}"
        
        print('Back to the model!')
        return {'messages': [HumanMessage(content=tool_response)]}
