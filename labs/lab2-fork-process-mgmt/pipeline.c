#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: ./pipeline <number>\n");
        return 1;
    }

    int to_child[2];    
    int to_parent[2];   

    pipe(to_child);
    pipe(to_parent);

    int pid = fork();

    if (pid == 0) {
       
        close(to_child[1]);    
        close(to_parent[0]);   

        int n;
        read(to_child[0], &n, sizeof(n));   
        close(to_child[0]);

        long result = 1;
        for (int i = 2; i <= n; i++) result *= i;  

        write(to_parent[1], &result, sizeof(result));
        close(to_parent[1]);
    } else {
       
        close(to_child[0]);    
        close(to_parent[1]);  

        int n = atoi(argv[1]);
        write(to_child[1], &n, sizeof(n));
        close(to_child[1]);    

        long result;
        read(to_parent[0], &result, sizeof(result));
        close(to_parent[0]);

        printf("Result: %ld\n", result);
        wait(NULL);
    }

    return 0;
}