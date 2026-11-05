import streamlit as st


def authenticated_menu():
    # Show a navigation menu for authenticated users
    # st.sidebar.page_link("main.py", label="Switch accounts")
    st.sidebar.page_link("pages/dashboard.py", label="Dashboard")
    st.sidebar.page_link("pages/logout.py", label="Logout")
    # if st.session_state.role in ["admin", "super-admin"]:
    #     st.sidebar.page_link("pages/admin.py", label="Manage users")
    #     st.sidebar.page_link(
    #         "pages/super-admin.py",
    #         label="Manage admin access",
    #         disabled=st.session_state.role != "super-admin",
    #     )


def unauthenticated_menu():
    # Show a navigation menu for unauthenticated users
    st.sidebar.page_link("main.py", label="Log in") 
    st.sidebar.page_link("pages/signup.py", label="Signup")
    st.sidebar.page_link("pages/reset_password.py", label="Reset Password")


def menu():
    # Determine if a user is logged in or not, then show the correct
    # navigation menu
    if ("role" not in st.session_state or st.session_state.role is None) or ('account' not in st.session_state or st.session_state.account is None) :
        unauthenticated_menu()
        return
    authenticated_menu()


def menu_with_redirect():
    # Redirect users to the main page if not logged in, otherwise continue to
    # render the navigation menu
    if ("role" not in st.session_state or st.session_state.role is None) or ('account' not in st.session_state or st.session_state.account is None) :
        st.switch_page("main.py")
    menu()

