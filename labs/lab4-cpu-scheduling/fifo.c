#include <stdio.h>
#include <stdlib.h>   /* atoi(), malloc(), free() */

int main(int argc, char *argv[])
{
    if (argc < 2) {
        printf("Usage: ./fifo <num_jobs> <burst1> ...\n");
        exit(1);
    }

    int n = atoi(argv[1]);
    if (n <= 0 || argc != 2 + n) {
        printf("Usage: ./fifo <num_jobs> <burst1> ...\n");
        exit(1);
    }

    int *burst      = malloc(n * sizeof(int));
    int *turnaround = malloc(n * sizeof(int));
    int *response   = malloc(n * sizeof(int));
    if (!burst || !turnaround || !response) {
        printf("Memory allocation failed\n");
        exit(1);
    }

    for (int i = 0; i < n; i++)
        burst[i] = atoi(argv[2 + i]);

    /* FIFO: each job runs to completion in arrival order */
    int time = 0;
    for (int i = 0; i < n; i++) {
        response[i]   = time;
        time         += burst[i];
        turnaround[i] = time;
    }

    double total_t = 0, total_r = 0;
    for (int i = 0; i < n; i++) {
        printf("Job %d: T=%d R=%d\n", i + 1, turnaround[i], response[i]);
        total_t += turnaround[i];
        total_r += response[i];
    }
    printf("Average T=%.2f Average R=%.2f\n", total_t / n, total_r / n);

    free(burst);
    free(turnaround);
    free(response);
    return 0;
}
