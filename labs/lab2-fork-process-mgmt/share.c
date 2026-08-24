#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: ./program_name <integer>\n");
        exit(1);
    }

    int x = atoi(argv[1]);

    printf("Original Value : %d\n", x);
    fflush(stdout);  

    int pid = fork();

    if (pid == 0) {
        
        x = x - 42;
        printf("child : x=%d\n", x);
    } else {
       
        wait(NULL);
        x = x + 13;
        printf("mother : x=%d\n", x);
    }

    return 0;
}