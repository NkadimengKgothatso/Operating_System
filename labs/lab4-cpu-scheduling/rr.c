#include <stdio.h>
#include <stdlib.h>   /* atoi(), malloc(), free() */

int main(int argc, char *argv[])
{
    if (argc < 3) {
        printf("Usage: ./rr <quantum> <num_jobs> <burst1> ...\n");
        exit(1);
    }

    int quantum = atoi(argv[1]);
    int n       = atoi(argv[2]);
    if (quantum <= 0 || n <= 0 || argc != 3 + n) {
        printf("Usage: ./rr <quantum> <num_jobs> <burst1> ...\n");
        exit(1);
    }

    int *remaining  = malloc(n * sizeof(int));
    int *turnaround = malloc(n * sizeof(int));
    int *response   = malloc(n * sizeof(int));
    int *responded  = malloc(n * sizeof(int));
    if (!remaining || !turnaround || !response || !responded) {
        printf("Memory allocation failed\n");
        exit(1);
    }

    for (int i = 0; i < n; i++) {
        remaining[i]  = atoi(argv[3 + i]);
        responded[i]  = 0;
        turnaround[i] = 0;
        response[i]   = 0;
    }

    /* Round Robin: each job runs for at most one quantum per round */
    int time = 0;
    int done = 0;
    while (done < n) {
        done = 0;
        for (int i = 0; i < n; i++) {
            if (remaining[i] == 0) { done++; continue; }
            if (!responded[i])     { response[i] = time; responded[i] = 1; }
            int run       = (remaining[i] < quantum) ? remaining[i] : quantum;
            remaining[i] -= run;
            time         += run;
            if (remaining[i] == 0) { turnaround[i] = time; done++; }
        }
    }

    double total_t = 0, total_r = 0;
    for (int i = 0; i < n; i++) {
        printf("Job %d: T=%d R=%d\n", i + 1, turnaround[i], response[i]);
        total_t += turnaround[i];
        total_r += response[i];
    }
    printf("Average T=%.2f Average R=%.2f\n", total_t / n, total_r / n);

    free(remaining);
    free(turnaround);
    free(response);
    free(responded);
    return 0;
}
