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

    int pid = fork();

    if (pid == 0) {
       
        return x * 2;
    } else {
        
        int res;
        wait(&res);
        printf("%d\n", WEXITSTATUS(res));
    }

    return 0;
}