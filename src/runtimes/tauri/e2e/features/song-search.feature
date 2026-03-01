Feature: Song Search
  As a karaoke user
  I want to search for songs in the library
  So that I can find and queue songs to sing

  Scenario: Searching for a song updates the status bar
    Given the application is running
    And the backend is connected
    When the user searches for "Coulton"
    Then the status bar should indicate search results or a search action

  Scenario: Search with Enter key triggers search
    Given the application is running
    And the backend is connected
    When the user types "Coulton" in the search input
    And the user presses Enter in the search input
    Then the status bar should indicate search results or a search action

  Scenario: Incremental search triggers after typing
    Given the application is running
    And the backend is connected
    When the user types "test" in the search input
    Then the application should send a search request after a short delay
