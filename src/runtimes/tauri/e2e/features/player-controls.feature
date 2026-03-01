Feature: Player Controls
  As a karaoke DJ
  I want to control playback with dedicated buttons
  So that I can manage the karaoke session smoothly

  Scenario: Play button is clickable and does not crash the app
    Given the application is running
    When the user clicks the play button
    Then the app should remain stable

  Scenario: Stop button is clickable and does not crash the app
    Given the application is running
    When the user clicks the stop button
    Then the app should remain stable

  Scenario: Next track button is clickable and does not crash the app
    Given the application is running
    When the user clicks the next track button
    Then the app should remain stable

  Scenario: Previous track button is clickable and does not crash the app
    Given the application is running
    When the user clicks the previous track button
    Then the app should remain stable

  Scenario: Volume slider adjusts volume display
    Given the application is running
    When the user sets the volume slider to 50
    Then the volume display should show "50%"

  Scenario: All player buttons are clickable without crashing
    Given the application is running
    Then every visible button should be clickable without crashing the app
