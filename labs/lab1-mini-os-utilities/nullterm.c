#include <stdio.h>
#include <stdlib.h>
#include <string.h>


int main(int argc, char *argv[]) {
    char buffer[10];

    if (argc == 2) {
        strncpy(buffer, argv[1], sizeof(buffer));
        buffer[sizeof(buffer) - 1] = '\0';
    } else {
        buffer[0] = '\0'; // no argument -> empty string
    }

   

  printf("Copied string: %s\n", buffer);
  printf("String length (strlen): %zu\n", strlen(buffer));

    return 0;
}