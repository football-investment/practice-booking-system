"""
Location Matrix Rendering
==========================

Main matrix rendering logic for a specific location.

- Render matrix header (age groups x years)
- Render matrix rows for each age group
- Render matrix cells with coverage data
"""

import streamlit as st
from datetime import datetime
from .gap_detection import calculate_coverage
from .matrix_cells import render_matrix_cell


def render_location_matrix_header(years: list):
    """
    Render the matrix header row with year columns

    Args:
        years: List of years to display
    """
    header_cols = st.columns([2] + [1] * len(years))
    with header_cols[0]:
        st.markdown("**Age Group**")
    for i, year in enumerate(years):
        with header_cols[i + 1]:
            st.markdown(f"**{year}**")


def render_age_group_label(age_group: str):
    """
    Render the age group label with cycle info

    Args:
        age_group: Age group name (PRE, YOUTH, AMATEUR, PRO)
    """
    if age_group == "PRE":
        st.markdown(f"**{age_group}**")
        st.caption("(Monthly: 12/year)")
    elif age_group == "YOUTH":
        st.markdown(f"**{age_group}**")
        st.caption("(Quarterly: 4/year)")
    elif age_group in ["AMATEUR", "PRO"]:
        st.markdown(f"**{age_group}**")
        st.caption("(Annual: 1/year)")


def render_matrix_row(
    token: str,
    semesters: list,
    age_group: str,
    years: list,
    location_id: int,
    user_role: str = "admin",
    is_master: bool = False
):
    """
    Render a single row for an age group across all years

    Args:
        token: Auth token
        semesters: List of semesters for the location
        age_group: Age group (PRE, YOUTH, AMATEUR, PRO)
        years: List of years to display
        location_id: Location ID
        user_role: User role (admin, instructor, etc.)
        is_master: Whether current user is master instructor
    """
    row_cols = st.columns([2] + [1] * len(years))

    # Age group label with cycle info
    with row_cols[0]:
        render_age_group_label(age_group)

    # Year cells
    for i, year in enumerate(years):
        with row_cols[i + 1]:
            coverage = calculate_coverage(semesters, age_group, year)
            render_matrix_cell(
                token,
                semesters,
                age_group,
                year,
                location_id,
                coverage,
                user_role,
                is_master
            )

    st.divider()


def render_coverage_matrix(
    token: str,
    semesters: list,
    years: list,
    location_id: int,
    user_role: str = "admin",
    is_master: bool = False
):
    """
    Render the complete coverage matrix for a location

    Args:
        token: Auth token
        semesters: List of semesters for the location
        years: List of years to display
        location_id: Location ID
        user_role: User role (admin, instructor, etc.)
        is_master: Whether current user is master instructor
    """
    age_groups = ["PRE", "YOUTH", "AMATEUR", "PRO"]

    # Header row
    render_location_matrix_header(years)
    st.divider()

    # Data rows
    for age_group in age_groups:
        render_matrix_row(
            token,
            semesters,
            age_group,
            years,
            location_id,
            user_role,
            is_master
        )


def render_legend():
    """
    Render the legend explaining matrix cell statuses
    """
    st.markdown("#### Legend")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("Full Coverage")
        st.caption("All periods generated")
        st.caption("Click [Manage] to edit")

    with col2:
        st.warning("Partial Coverage")
        st.caption("Some periods missing")
        st.caption("Click [+ X More] to generate missing")

    with col3:
        st.error("No Coverage")
        st.caption("No periods generated")
        st.caption("Click [+ Generate] to create all")
