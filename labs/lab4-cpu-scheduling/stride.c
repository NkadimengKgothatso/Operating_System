#include <stdio.h>
#include <stdlib.h>   /* atoi(), malloc(), free() */

#define STRIDE_CONST 10000

int main(int argc, char *argv[])
{
    if (argc < 2) {
        printf("Usage: ./stride <num_jobs> <tickets1> <burst1> ...\n");
        exit(1);
    }

    int n = atoi(argv[1]);
    if (n <= 0 || argc != 2 + 2 * n) {
        printf("Usage: ./stride <num_jobs> <tickets1> <burst1> ...\n");
        exit(1);
    }

    int *tickets    = malloc(n * sizeof(int));
    int *stride     = malloc(n * sizeof(int));
    int *pass       = malloc(n * sizeof(int));
    int *remaining  = malloc(n * sizeof(int));
    int *turnaround = malloc(n * sizeof(int));
    int *response   = malloc(n * sizeof(int));
    int *responded  = malloc(n * sizeof(int));
    if (!tickets || !stride || !pass || !remaining ||
        !turnaround || !response || !responded) {
        printf("Memory allocation failed\n");
        exit(1);
    }

    int total_work = 0;
    for (int i = 0; i < n; i++) {
        tickets[i]   = atoi(argv[2 + i * 2]);
        remaining[i] = atoi(argv[3 + i * 2]);
        if (tickets[i] <= 0) {
            printf("Usage: ./stride <num_jobs> <tickets1> <burst1> ...\n");
            exit(1);
        }
        stride[i]     = STRIDE_CONST / tickets[i];   /* integer division */
        pass[i]       = 0;
        responded[i]  = 0;
        response[i]   = 0;
        turnaround[i] = 0;
        if (remaining[i] > 0) total_work += remaining[i];
    }

    /* Stride: each tick, run the unfinished job with the smallest pass */
    int time = 0;
    for (int tick = 0; tick < total_work; tick++) {
        int j = -1;
        for (int i = 0; i < n; i++) {
            if (remaining[i] <= 0) continue;
            if (j == -1 || pass[i] < pass[j])   /* strict < keeps lowest index on ties */
                j = i;
        }
        if (j == -1) break;

        if (!responded[j]) { response[j] = time; responded[j] = 1; }
        remaining[j] -= 1;
        if (remaining[j] == 0) turnaround[j] = time + 1;
        pass[j] += stride[j];
        time    += 1;
    }

    double total_t = 0, total_r = 0;
    for (int i = 0; i < n; i++) {
        printf("Job %d: T=%d R=%d\n", i + 1, turnaround[i], response[i]);
        total_t += turnaround[i];
        total_r += response[i];
    }
    printf("Average T=%.2f Average R=%.2f\n", total_t / n, total_r / n);

    free(tickets);
    free(stride);
    free(pass);
    free(remaining);
    free(turnaround);
    free(response);
    free(responded);
    return 0;
}
