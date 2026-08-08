#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[]) {
    char buffer[1024];

    if (argc >= 2) {
        strncpy(buffer, argv[1], sizeof(buffer) - 1);
        buffer[sizeof(buffer) - 1] = '\0';
    } else {
        buffer[0] = '\0'; // no argument -> empty string
    }

    int count = 0;
    char *token = strtok(buffer, " ");
    while (token != NULL) {
        count++;
        token = strtok(NULL, " ");
    }
    printf("%d\n", count);
    return 0;
}